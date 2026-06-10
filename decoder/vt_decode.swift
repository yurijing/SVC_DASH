import VideoToolbox; import CoreMedia; import Foundation

let args = CommandLine.arguments
guard args.count > 1 else { print("Usage: vt_decode <file.264>"); exit(1) }
let inPath = args[1]

// Global state
var session: VTDecompressionSession?
var fmtDesc: CMVideoFormatDescription?
var width: Int32 = 0; var height: Int32 = 0
var outFd = FileHandle.standardOutput
var frameCount: Int32 = 0

// Decode callback
func onFrame(_: UnsafeMutableRawPointer?, _: UnsafeMutableRawPointer?,
             status: OSStatus, _: VTDecodeInfoFlags,
             imageBuffer: CVImageBuffer?, _: CMTime, _: CMTime) {
    guard status == noErr, let buf = imageBuffer else { return }
    CVPixelBufferLockBaseAddress(buf, .readOnly)
    defer { CVPixelBufferUnlockBaseAddress(buf, .readOnly) }

    let w = CVPixelBufferGetWidth(buf)
    let h = CVPixelBufferGetHeight(buf)
    let stride = CVPixelBufferGetBytesPerRow(buf)
    let base = CVPixelBufferGetBaseAddress(buf)!.assumingMemoryBound(to: UInt8.self)

    var rgb = [UInt8](repeating: 0, count: w * h * 3)
    for y in 0..<h {
        for x in 0..<w {
            let src = base.advanced(by: y * stride + x * 4)
            let dst = (y * w + x) * 3
            rgb[dst] = src[2]; rgb[dst+1] = src[1]; rgb[dst+2] = src[0] // BGRA→RGB
        }
    }

    var sz = UInt32(w * h * 3).bigEndian
    withUnsafeBytes(of: &sz) { outFd.write(Data($0)) }
    outFd.write(Data(rgb))
    frameCount += 1
}

// Feed NAL unit to decoder
func feed(_ nal: [UInt8], _ pts: Int64) {
    guard let session = session, !nal.isEmpty else { return }
    var nalLen = UInt32(nal.count).bigEndian
    var nalData = Data()
    withUnsafeBytes(of: &nalLen) { nalData.append(Data($0)) }
    nalData.append(Data(nal))

    var blockBuf: CMBlockBuffer?
    nalData.withUnsafeBytes { ptr in
        CMBlockBufferCreateWithMemoryBlock(
            allocator: kCFAllocatorDefault, memoryBlock: nil,
            blockLength: nalData.count, blockAllocator: kCFAllocatorDefault,
            customBlockSource: nil, offsetToData: 0, dataLength: nalData.count,
            flags: 0, blockBufferOut: &blockBuf)
    }
    guard var bb = blockBuf else { return }
    defer { CFRelease(bb) }

    CMBlockBufferReplaceDataBytes(with: nalData, blockBuffer: &bb, offsetIntoDestination: 0, dataLength: nalData.count)

    var sampleBuf: CMSampleBuffer?
    var timing = CMSampleTimingInfo(
        duration: CMTime(value: 1, timescale: 24),
        presentationTimeStamp: CMTime(value: pts, timescale: 24),
        decodeTimeStamp: .invalid)
    CMSampleBufferCreateReady(
        allocator: kCFAllocatorDefault, dataBuffer: bb,
        formatDescription: fmtDesc, sampleCount: 1, sampleTimingEntryCount: 1,
        sampleTimingArray: &timing, sampleSizeEntryCount: 0,
        sampleSizeArray: nil, sampleBufferOut: &sampleBuf)
    guard var sb = sampleBuf else { return }
    defer { CFRelease(sb) }

    VTDecompressionSessionDecodeFrame(session, &sb, [], nil, nil)
}

// Main
func processFile(_ path: String) {
    guard let data = try? Data(contentsOf: URL(fileURLWithPath: path)) else { return }
    let bytes = [UInt8](data); let n = bytes.count
    guard n > 4 else { return }

    // Find SPS/PPS (only once)
    if fmtDesc == nil {
        var sps: [UInt8] = [], pps: [UInt8] = []
        var i = 0
        while i < n - 3 {
            if bytes[i]==0 && bytes[i+1]==0 && bytes[i+2]==0 && bytes[i+3]==1 {
                let t = Int(bytes[i+4]) & 0x1F
                var end = n
                for j in (i+5)..<(n-3) {
                    if bytes[j]==0 && bytes[j+1]==0 && bytes[j+2]==0 && bytes[j+3]==1 { end = j; break }
                }
                if t == 7 { sps = Array(bytes[(i+4)..<end]) }
                if t == 8 { pps = Array(bytes[(i+4)..<end]) }
                i = end
            } else { i += 1 }
        }
        guard !sps.isEmpty, !pps.isEmpty else { return }

        sps.withUnsafeBufferPointer { sp in
            pps.withUnsafeBufferPointer { pp in
                var ptrs: [UnsafePointer<UInt8>] = [sp.baseAddress!, pp.baseAddress!]
                var sizes: [Int] = [sps.count, pps.count]
                CMVideoFormatDescriptionCreateFromH264ParameterSets(
                    allocator: kCFAllocatorDefault, parameterSetCount: 2,
                    parameterSetPointers: &ptrs, parameterSetSizes: &sizes,
                    nalUnitHeaderLength: 4, formatDescriptionOut: &fmtDesc)
            }
        }
        guard let desc = fmtDesc else { return }
        let dims = CMVideoFormatDescriptionGetDimensions(desc)
        width = dims.width; height = dims.height

        // Create session
        var cb = VTDecompressionOutputCallbackRecord(
            decompressionOutputCallback: onFrame, decompressionOutputRefCon: nil)
        var pxFmt = kCVPixelFormatType_32BGRA
        var w32 = width; var h32 = height
        var pxFmtNum = CFNumberCreate(kCFAllocatorDefault, .sInt32Type, &pxFmt)!
        var pxW = CFNumberCreate(kCFAllocatorDefault, .intType, &w32)!
        var pxH = CFNumberCreate(kCFAllocatorDefault, .intType, &h32)!
        defer { CFRelease(pxFmtNum); CFRelease(pxW); CFRelease(pxH) }
        let keys = [kCVPixelBufferPixelFormatTypeKey, kCVPixelBufferWidthKey, kCVPixelBufferHeightKey] as CFArray
        let vals = [pxFmtNum, pxW, pxH] as CFArray
        var pxAttrs = CFDictionaryCreate(kCFAllocatorDefault,
            unsafeBitCast(keys, to: UnsafePointer<UnsafeRawPointer?>.self),
            unsafeBitCast(vals, to: UnsafePointer<UnsafeRawPointer?>.self), 3,
            nil, nil)!
        defer { CFRelease(pxAttrs) }
        VTDecompressionSessionCreate(allocator: kCFAllocatorDefault,
            formatDescription: desc, videoDecoderSpecification: nil,
            destinationImageBufferAttributes: pxAttrs,
            outputCallback: &cb, decompressionSessionOut: &session)
    }

    guard let session = session, var sps: [UInt8] = nil else { return }
    // Rescan for SPS/PPS
    var sps2: [UInt8] = [], pps2: [UInt8] = []
    var i = 0
    while i < n - 3 {
        if bytes[i]==0 && bytes[i+1]==0 && bytes[i+2]==0 && bytes[i+3]==1 {
            let t = Int(bytes[i+4]) & 0x1F
            var end = n
            for j in (i+5)..<(n-3) {
                if bytes[j]==0 && bytes[j+1]==0 && bytes[j+2]==0 && bytes[j+3]==1 { end = j; break }
            }
            if t == 7 { sps2 = Array(bytes[(i+4)..<end]) }
            if t == 8 { pps2 = Array(bytes[(i+4)..<end]) }
            i = end
        } else { i += 1 }
    }
    guard !sps2.isEmpty, !pps2.isEmpty else { return }

    var pts: Int64 = frameCount
    i = 0
    while i < n - 3 {
        if bytes[i]==0 && bytes[i+1]==0 && bytes[i+2]==0 && bytes[i+3]==1 {
            let t = Int(bytes[i+4]) & 0x1F
            var end = n
            for j in (i+5)..<(n-3) {
                if bytes[j]==0 && bytes[j+1]==0 && bytes[j+2]==0 && bytes[j+3]==1 { end = j; break }
            }
            if t == 1 || t == 5 {
                feed(sps2, pts); feed(pps2, pts)
                feed(Array(bytes[(i+4)..<end]), pts)
                pts += 1
            }
            i = end
        } else { i += 1 }
    }
}

// Run: process file, wait for async frames
processFile(inPath)
if let s = session {
    VTDecompressionSessionWaitForAsynchronousFrames(s)
    VTDecompressionSessionFinishDelayedFrames(s)
    VTDecompressionSessionInvalidate(s)
}
