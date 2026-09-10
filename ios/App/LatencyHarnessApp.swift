// LatencyHarnessApp.swift
//
// Entry point. This is an instrument, not a product: one screen, no navigation,
// no camera. See ios/README.md for what it measures and why it exists (P0-0/P0-2 —
// on-device Core ML latency, which nothing else in this repo can produce, because
// Xcode's Core ML Performance Report is Mac-only and there is no Mac).

import SwiftUI

@main
struct LatencyHarnessApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
