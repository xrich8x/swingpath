// ModelRunner.swift
//
// Loads a Core ML model bundle found in the app's Documents directory and times
// its `prediction(from:)` call. Two design choices worth flagging, since neither
// can be checked without a Mac:
//
// 1. `MLModel.compileModel(at:)` is a public, documented on-device runtime API
//    (available since iOS 11, extended to accept `.mlpackage` directories, not
//    only `.mlmodel` files) that compiles a model to a temporary `.mlmodelc` and
//    hands back its URL. That is DIFFERENT from Xcode's build-time compile, which
//    only fires when a `.mlpackage` is a project resource — we deliberately do not
//    do that (see ios/README.md "How models get onto the device"), so this
//    runtime call is the only compile step in this app. High confidence this is
//    correct (it is exactly the mechanism Apple documents for downloadable/
//    post-install models), but it has not been exercised by an actual build here.
// 2. The pose model's exact Core ML input feature name/type (ultralytics' native
//    coreml export, `nms=True`) is unknown without inspecting the exported
//    `.mlpackage` on a Mac, which this environment does not have. Rather than
//    guess a name, `dummyInput(for:)` below reads `model.modelDescription` and
//    manufactures a zero-filled value for WHATEVER inputs are actually declared,
//    for both the ball model and the pose model, with no per-model special case.

import CoreML
import CoreVideo
import Foundation

enum RunnerError: Error, CustomStringConvertible {
    case compileFailed(String)
    case loadFailed(String)
    case predictFailed(String)
    case unsupportedFeature(String)

    var description: String {
        switch self {
        case .compileFailed(let s): return "compile failed: \(s)"
        case .loadFailed(let s): return "load failed: \(s)"
        case .predictFailed(let s): return "predict failed: \(s)"
        case .unsupportedFeature(let s): return "unsupported model feature: \(s)"
        }
    }
}

enum ModelRunner {

    /// Compiles (on-device, at runtime) and loads a model found at `packageURL`,
    /// which may be a `.mlpackage` directory, a `.mlmodel` file, or an already-
    /// compiled `.mlmodelc` directory (compileModel is a harmless no-op-ish path
    /// for the latter — Core ML still accepts it).
    ///
    /// Compute units are pinned to `.cpuAndNeuralEngine`, never `.all`: this
    /// project standardised on that pin for the main app because GPU submission
    /// from the background is refused on iOS, and there is no reason for this
    /// harness to measure a different compute-unit configuration than what the
    /// product will actually ship (see tools/export_coreml_p0.py's
    /// `ct.ComputeUnit.CPU_AND_NE`, which this mirrors).
    static func loadCompiled(from packageURL: URL) async throws -> MLModel {
        let compiledURL: URL
        do {
            compiledURL = try await MLModel.compileModel(at: packageURL)
        } catch {
            throw RunnerError.compileFailed("\(packageURL.lastPathComponent): \(error)")
        }
        let config = MLModelConfiguration()
        config.computeUnits = .cpuAndNeuralEngine
        do {
            return try MLModel(contentsOf: compiledURL, configuration: config)
        } catch {
            throw RunnerError.loadFailed("\(packageURL.lastPathComponent): \(error)")
        }
    }

    /// Builds one feature-provider input with a zero-filled value for every input
    /// the model declares, read from the model's own description. This is what
    /// lets one code path cover BallNet's known `frames` (1,9,288,512) MLMultiArray
    /// input AND yolo11m-pose's input (name/type unknown to us) without hardcoding
    /// either. The VALUES fed in are irrelevant to a latency measurement — only the
    /// shape/type has to be right for the model to run at all.
    static func dummyInput(for model: MLModel) throws -> MLFeatureProvider {
        var values: [String: Any] = [:]

        for (name, desc) in model.modelDescription.inputDescriptionsByName {
            switch desc.type {
            case .multiArray:
                guard let constraint = desc.multiArrayConstraint else {
                    throw RunnerError.unsupportedFeature("\(name): multiArray with no constraint")
                }
                let array = try MLMultiArray(shape: constraint.shape, dataType: constraint.dataType)
                let count = array.count
                for i in 0..<count { array[i] = 0 }
                values[name] = array

            case .image:
                guard let constraint = desc.imageConstraint else {
                    throw RunnerError.unsupportedFeature("\(name): image with no constraint")
                }
                let width = constraint.pixelsWide
                let height = constraint.pixelsHigh
                var pixelBuffer: CVPixelBuffer?
                let status = CVPixelBufferCreate(
                    kCFAllocatorDefault, width, height,
                    constraint.pixelFormatType, nil, &pixelBuffer
                )
                guard status == kCVReturnSuccess, let buffer = pixelBuffer else {
                    throw RunnerError.unsupportedFeature("\(name): could not allocate a \(width)x\(height) pixel buffer")
                }
                CVPixelBufferLockBaseAddress(buffer, [])
                if let base = CVPixelBufferGetBaseAddress(buffer) {
                    let bytesPerRow = CVPixelBufferGetBytesPerRow(buffer)
                    memset(base, 0, bytesPerRow * height)
                }
                CVPixelBufferUnlockBaseAddress(buffer, [])
                values[name] = buffer

            case .double:
                values[name] = 0.0

            case .int64:
                values[name] = 0

            case .string:
                values[name] = ""

            case .dictionary, .sequence, .invalid:
                throw RunnerError.unsupportedFeature("\(name): feature type \(desc.type.rawValue) not handled by this harness")

            @unknown default:
                throw RunnerError.unsupportedFeature("\(name): unknown feature type")
            }
        }

        return try MLDictionaryFeatureProvider(dictionary: values)
    }

    /// Times exactly one `prediction(from:)` call against an already-built input.
    /// Building the input is deliberately NOT part of this function — see
    /// `measure` below for why.
    static func measureOnce(model: MLModel, input: MLFeatureProvider) throws -> LatencySample {
        let start = DispatchTime.now().uptimeNanoseconds
        _ = try model.prediction(from: input)
        let end = DispatchTime.now().uptimeNanoseconds
        let ms = Double(end - start) / 1_000_000.0
        return LatencySample(ms: ms, thermalState: ProcessInfo.processInfo.thermalState)
    }

    /// Runs `warmupRuns` untimed predictions (ANE kernel compilation, caches
    /// warming up) then `timedRuns` timed ones, one sample per call, all against
    /// the SAME `input` value. Call this off the main thread — `prediction(from:)`
    /// is synchronous and blocking.
    ///
    /// `input` is a parameter, not built internally, because `runSweep`'s
    /// sustained loop calls this (and `measureOnce`) once per single sample: if
    /// each call rebuilt a fresh dummy input (BallNet's is a 1,327,104-element
    /// MLMultiArray), the sustained run would spend more CPU time — and generate
    /// more heat — building throwaway inputs than running the model, which would
    /// confound exactly the thermal measurement this harness exists to make.
    static func measure(model: MLModel, input: MLFeatureProvider, warmupRuns: Int, timedRuns: Int) throws -> [LatencySample] {
        for _ in 0..<warmupRuns {
            _ = try model.prediction(from: input)
        }
        var samples: [LatencySample] = []
        samples.reserveCapacity(timedRuns)
        for _ in 0..<timedRuns {
            samples.append(try measureOnce(model: model, input: input))
        }
        return samples
    }

    /// The full per-model sweep: one quick block (baseline once warm) then a
    /// bucketed sustained block for `sustainedMinutes` (0 skips it). `log` is
    /// called with one formatted line per event — the caller (the view model)
    /// hops it back to the main thread; this function itself does not touch UI
    /// state and is safe to call from any background queue/thread.
    ///
    /// The sustained block is the one that answers the thermal-steady-state
    /// question this whole harness exists for: bucketing means a degrading
    /// median over the run is visible in the log, not averaged away into one
    /// number that hides exactly the effect being measured.
    static func runSweep(model: MLModel, sustainedMinutes: Int, log: @escaping (String) -> Void) throws {
        // Built ONCE for the whole sweep (quick block + every sustained sample)
        // — see measure()'s doc comment for why rebuilding it per-sample would
        // corrupt the thermal measurement.
        let input = try dummyInput(for: model)

        let quick = try measure(model: model, input: input, warmupRuns: 10, timedRuns: 50)
        let quickMs = quick.map { $0.ms }
        log(String(format: "quick (50 runs): median %.2f ms, p95 %.2f ms, thermal %@",
                    quickMs.median(), quickMs.percentile(95),
                    thermalStateLabel(quick.last?.thermalState ?? .nominal)))

        let totalSeconds = Double(sustainedMinutes) * 60.0
        guard totalSeconds > 0 else { return }

        let bucketSeconds = 30.0
        let deadline = Date().addingTimeInterval(totalSeconds)
        var bucket: [Double] = []
        var bucketStart = Date()
        var elapsedSeconds = 0

        while Date() < deadline {
            let sample = try measureOnce(model: model, input: input)
            bucket.append(sample.ms)
            if Date().timeIntervalSince(bucketStart) >= bucketSeconds {
                elapsedSeconds += Int(bucketSeconds)
                log(String(format: "sustained t+%ds: n=%d median %.2f ms, p95 %.2f ms, thermal %@",
                            elapsedSeconds, bucket.count, bucket.median(), bucket.percentile(95),
                            thermalStateLabel(sample.thermalState)))
                bucket = []
                bucketStart = Date()
            }
        }
        if !bucket.isEmpty {
            log(String(format: "sustained (final partial bucket): n=%d median %.2f ms, p95 %.2f ms",
                        bucket.count, bucket.median(), bucket.percentile(95)))
        }
    }
}
