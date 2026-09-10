// ResultsLogger.swift
//
// Appends result lines to Documents/harness_session_log.txt as they are produced,
// not just at the end of a run. There is no Mac in this project, so there is no
// Xcode console or Instruments trace to read afterwards — the on-screen list and
// this file (retrievable the same way models arrive, via the Files app / Apple
// Devices File Sharing) are the ONLY way results leave the device. Writing
// incrementally means a run interrupted (backgrounded, killed, phone locked even
// with the idle timer disabled) still leaves a partial, honest record rather than
// nothing — the same "design for interruption" principle the product itself uses.

import Foundation

final class ResultsLogger {
    private let fileURL: URL
    private var handle: FileHandle?

    init(fileName: String = "harness_session_log.txt") {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        self.fileURL = docs.appendingPathComponent(fileName)
        if !FileManager.default.fileExists(atPath: fileURL.path) {
            FileManager.default.createFile(atPath: fileURL.path, contents: nil)
        }
        self.handle = try? FileHandle(forWritingTo: fileURL)
        self.handle?.seekToEndOfFile()
    }

    func append(_ line: String) {
        guard let handle = handle else { return }
        let text = line + "\n"
        if let data = text.data(using: .utf8) {
            handle.write(data)
        }
    }

    func appendSessionHeader() {
        let df = ISO8601DateFormatter()
        append("")
        append("==== session \(df.string(from: Date())) ====")
    }

    var path: String { fileURL.path }
}
