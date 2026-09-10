// Stats.swift
//
// Plain median/percentile helpers over a [Double] of millisecond samples. No
// dependency, no library — this is small enough that pulling in a stats package
// would be a first-build risk for zero benefit (constraint: no dependency whose
// resolution can't be verified here, since there is no Mac to test the resolve).

import Foundation

extension Array where Element == Double {
    /// Standard median: average the two middle values on an even count.
    func median() -> Double {
        guard !isEmpty else { return .nan }
        let sorted = self.sorted()
        let mid = sorted.count / 2
        if sorted.count % 2 == 0 {
            return (sorted[mid - 1] + sorted[mid]) / 2.0
        }
        return sorted[mid]
    }

    /// Linear-interpolation percentile (the common "type 7" definition). p in [0, 100].
    func percentile(_ p: Double) -> Double {
        guard !isEmpty else { return .nan }
        if count == 1 { return self[0] }
        let sorted = self.sorted()
        let rank = (p / 100.0) * Double(sorted.count - 1)
        let lower = Int(rank.rounded(.down))
        let upper = Int(rank.rounded(.up))
        if lower == upper { return sorted[lower] }
        let frac = rank - Double(lower)
        return sorted[lower] + (sorted[upper] - sorted[lower]) * frac
    }
}

/// One millisecond-latency measurement plus the thermal state at the moment it was
/// taken. Sustained throughput at thermal steady state is one of the three decisions
/// this whole harness exists to settle, so every sample carries this for free.
struct LatencySample {
    let ms: Double
    let thermalState: ProcessInfo.ThermalState
}

func thermalStateLabel(_ state: ProcessInfo.ThermalState) -> String {
    switch state {
    case .nominal: return "nominal"
    case .fair: return "fair"
    case .serious: return "serious"
    case .critical: return "critical"
    @unknown default: return "unknown"
    }
}
