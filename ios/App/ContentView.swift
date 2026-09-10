// ContentView.swift
//
// The entire UI: a model list, a Run/Run All button, a duration control, and a
// results log. Deliberately not a product screen — no camera, no navigation, no
// styling beyond what makes the numbers legible. See ios/README.md for how models
// get onto the device and how to read what this prints.

import SwiftUI
import CoreML
import UIKit

/// Owns model discovery, loading and the measurement sweep. Plain ObservableObject
/// (NOT @MainActor) so the heavy synchronous work can run on a background
/// DispatchQueue without fighting actor isolation; every @Published mutation is
/// explicitly hopped to the main queue instead. This trades a little verbosity for
/// avoiding Swift concurrency/actor-isolation edge cases in code nobody here can
/// compile-check before it reaches CI.
final class HarnessViewModel: ObservableObject {
    @Published var discoveredModels: [URL] = []
    @Published var log: [String] = []
    @Published var isRunning: Bool = false
    @Published var sustainedMinutes: Int = 2
    @Published var thermalNow: String = thermalStateLabel(ProcessInfo.processInfo.thermalState)

    // Not @Published: touched only from the single background queue this class
    // runs measurement work on, and `isRunning` gates against two overlapping
    // background runs, so there is never concurrent access to this dictionary.
    private var modelCache: [String: MLModel] = [:]

    private let logger = ResultsLogger()

    init() {
        logger.appendSessionHeader()
        appendLog("results also being written live to: \(logger.path)")
        rescan()
    }

    var documentsPath: String {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].path
    }

    func rescan() {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let recognizedExtensions = ["mlpackage", "mlmodelc", "mlmodel"]
        guard let items = try? FileManager.default.contentsOfDirectory(
            at: docs, includingPropertiesForKeys: nil, options: [.skipsHiddenFiles]
        ) else {
            appendLog("could not list Documents directory")
            return
        }
        discoveredModels = items
            .filter { recognizedExtensions.contains($0.pathExtension.lowercased()) }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
        appendLog("rescanned Documents: \(discoveredModels.count) model bundle(s) found")
        for m in discoveredModels { appendLog("  found: \(m.lastPathComponent)") }
    }

    func refreshThermalState() {
        thermalNow = thermalStateLabel(ProcessInfo.processInfo.thermalState)
    }

    func appendLog(_ line: String) {
        log.append(line)
        logger.append(line)
    }

    func copyLogToPasteboard() {
        UIPasteboard.general.string = log.joined(separator: "\n")
    }

    /// Loads (compiling on-device if needed) and caches the model at `url`. Must
    /// only be called from the background queue `runAll`/`runModel` dispatch onto.
    private func cachedModel(for url: URL) throws -> MLModel {
        if let cached = modelCache[url.path] {
            return cached
        }
        let model = try Self.syncAwait { try await ModelRunner.loadCompiled(from: url) }
        modelCache[url.path] = model
        return model
    }

    /// Bridges a `async throws` call into this synchronous, background-queue
    /// context. Safe from deadlock because the `Task` runs on Swift's cooperative
    /// thread pool while the semaphore blocks a plain DispatchQueue thread — two
    /// separate pools, so there is nothing for the wait to block on.
    private static func syncAwait<T>(_ operation: @escaping () async throws -> T) throws -> T {
        let sema = DispatchSemaphore(value: 0)
        var outcome: Result<T, Error>!
        Task {
            do {
                outcome = .success(try await operation())
            } catch {
                outcome = .failure(error)
            }
            sema.signal()
        }
        sema.wait()
        return try outcome.get()
    }

    func runModel(at url: URL) {
        runAll(only: [url])
    }

    /// Runs every model in `only` (or every discovered model if nil) sequentially
    /// on one background queue. Sequential, not parallel: two models timing each
    /// other's ANE/CPU contention would make every number unusable for the
    /// decisions this harness exists to inform.
    func runAll(only: [URL]? = nil) {
        guard !isRunning else { return }
        let urls = only ?? discoveredModels
        guard !urls.isEmpty else {
            appendLog("no model bundles found in Documents — see ios/README.md for how to get one there")
            return
        }
        isRunning = true
        UIApplication.shared.isIdleTimerDisabled = true
        let minutes = sustainedMinutes

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            for url in urls {
                let name = url.lastPathComponent
                DispatchQueue.main.async { self.appendLog("--- \(name) ---") }
                do {
                    let model = try self.cachedModel(for: url)
                    DispatchQueue.main.async { self.appendLog("loaded \(name), compute units = cpuAndNeuralEngine") }
                    try ModelRunner.runSweep(model: model, sustainedMinutes: minutes) { line in
                        DispatchQueue.main.async {
                            self.appendLog(line)
                            self.refreshThermalState()
                        }
                    }
                    DispatchQueue.main.async { self.appendLog("done: \(name)") }
                } catch {
                    DispatchQueue.main.async { self.appendLog("ERROR \(name): \(error)") }
                }
            }
            DispatchQueue.main.async {
                UIApplication.shared.isIdleTimerDisabled = false
                self.isRunning = false
            }
        }
    }
}

struct ContentView: View {
    @StateObject private var viewModel = HarnessViewModel()

    var body: some View {
        NavigationView {
            VStack(alignment: .leading, spacing: 12) {

                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text("Core ML latency harness")
                            .font(.headline)
                        Spacer()
                        Text("thermal: \(viewModel.thermalNow)")
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(Color.gray.opacity(0.2))
                            .cornerRadius(6)
                    }
                    Text("Instrument only — no camera, no UI polish. See ios/README.md.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal)

                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("Models (\(viewModel.discoveredModels.count))")
                            .font(.subheadline).bold()
                        Spacer()
                        Button("Rescan") { viewModel.rescan() }
                            .disabled(viewModel.isRunning)
                    }
                    if viewModel.discoveredModels.isEmpty {
                        Text("No .mlpackage / .mlmodelc / .mlmodel found in Documents. Transfer one — see ios/README.md.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    } else {
                        ForEach(viewModel.discoveredModels, id: \.self) { url in
                            HStack {
                                Text(url.lastPathComponent)
                                    .font(.system(.body, design: .monospaced))
                                    .lineLimit(1)
                                    .truncationMode(.middle)
                                Spacer()
                                Button("Run") { viewModel.runModel(at: url) }
                                    .disabled(viewModel.isRunning)
                            }
                        }
                    }
                }
                .padding(.horizontal)

                HStack {
                    Stepper(value: $viewModel.sustainedMinutes, in: 0...30) {
                        Text("Sustained run: \(viewModel.sustainedMinutes) min per model")
                            .font(.caption)
                    }
                    .disabled(viewModel.isRunning)
                }
                .padding(.horizontal)

                HStack {
                    Button(viewModel.isRunning ? "Running…" : "Run All") { viewModel.runAll() }
                        .disabled(viewModel.isRunning || viewModel.discoveredModels.isEmpty)
                        .buttonStyle(.borderedProminent)
                    Spacer()
                    Button("Copy results") { viewModel.copyLogToPasteboard() }
                }
                .padding(.horizontal)

                Divider()

                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 2) {
                            ForEach(Array(viewModel.log.enumerated()), id: \.offset) { idx, line in
                                Text(line)
                                    .font(.system(.caption, design: .monospaced))
                                    .id(idx)
                            }
                        }
                        .padding(.horizontal)
                    }
                    .onChange(of: viewModel.log.count) { _ in
                        if let last = viewModel.log.indices.last {
                            proxy.scrollTo(last, anchor: .bottom)
                        }
                    }
                }

                Text("Full log also at: \(viewModel.documentsPath)/harness_session_log.txt")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .padding(.horizontal)
                    .padding(.bottom, 4)
            }
            .navigationBarHidden(true)
            .onAppear {
                UIApplication.shared.isIdleTimerDisabled = viewModel.isRunning
            }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.didBecomeActiveNotification)) { _ in
                viewModel.rescan()
                viewModel.refreshThermalState()
            }
        }
    }
}
