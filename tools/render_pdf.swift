import Foundation
import AppKit
import PDFKit

guard CommandLine.arguments.count >= 3 else {
    fatalError("Usage: swift tools/render_pdf.swift INPUT.pdf OUTPUT_DIRECTORY")
}
let source = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
guard let document = PDFDocument(url: source) else { fatalError("Cannot read PDF") }
var pageInfo: [[String: Any]] = []
for index in 0..<document.pageCount {
    guard let page = document.page(at: index) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let image = page.thumbnail(of: NSSize(width: bounds.width * 1.6, height: bounds.height * 1.6), for: .mediaBox)
    guard let tiff = image.tiffRepresentation, let bitmap = NSBitmapImageRep(data: tiff),
          let data = bitmap.representation(using: .png, properties: [:]) else { fatalError("Cannot render") }
    try data.write(to: output.appendingPathComponent(String(format: "page-%02d.png", index + 1)))
    pageInfo.append(["page": index + 1, "text": page.string ?? "", "links": page.annotations.compactMap { $0.url?.absoluteString }])
}
let json = try JSONSerialization.data(withJSONObject: ["pages": document.pageCount, "content": pageInfo], options: [.prettyPrinted, .sortedKeys])
try json.write(to: output.appendingPathComponent("inspection.json"))
print("Rendered \(document.pageCount) pages")
