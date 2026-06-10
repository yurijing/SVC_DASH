/* vt_decode.m — macOS VideoToolbox H.264→RGB decoder.
   Compile: clang -framework VideoToolbox -framework CoreMedia -framework CoreVideo -framework CoreFoundation -O2 -o vt_decode vt_decode.m
   Usage: ./vt_decode <input.264>
   Output: raw RGB24 frames to stdout, each preceded by a 4-byte frame size (big-endian).
*/

#import <VideoToolbox/VideoToolbox.h>
#import <CoreMedia/CoreMedia.h>
#import <CoreVideo/CoreVideo.h>
#import <CoreFoundation/CoreFoundation.h>
#import <stdio.h>
#import <stdlib.h>
#import <string.h>
#import <unistd.h>
#import <fcntl.h>

// Global state
static VTDecompressionSessionRef session = NULL;
static CMVideoFormatDescriptionRef fmtDesc = NULL;
static int width = 0, height = 0;
static FILE *out = NULL;

// Decode callback — called when VT produces a frame
static void decode_callback(void *refCon, void *srcFrameRef,
    OSStatus status, VTDecodeInfoFlags flags,
    CVImageBufferRef imageBuffer, CMTime pts, CMTime duration)
{
    if (status != noErr || !imageBuffer) return;

    CVPixelBufferLockBaseAddress(imageBuffer, kCVPixelBufferLock_ReadOnly);

    int w = (int)CVPixelBufferGetWidth(imageBuffer);
    int h = (int)CVPixelBufferGetHeight(imageBuffer);
    int stride = (int)CVPixelBufferGetBytesPerRow(imageBuffer);
    uint8_t *base = (uint8_t *)CVPixelBufferGetBaseAddress(imageBuffer);
    OSType fmt = CVPixelBufferGetPixelFormatType(imageBuffer);

    // Convert to RGB24
    uint8_t rgb[w * h * 3];
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            uint8_t *pix = base + y * stride + x * 4;
            // BGRA → RGB
            rgb[(y * w + x) * 3 + 0] = pix[2];  // R
            rgb[(y * w + x) * 3 + 1] = pix[1];  // G
            rgb[(y * w + x) * 3 + 2] = pix[0];  // B
        }
    }

    CVPixelBufferUnlockBaseAddress(imageBuffer, kCVPixelBufferLock_ReadOnly);

    // Write frame size + data to stdout
    uint32_t sz = htonl(w * h * 3);
    fwrite(&sz, 4, 1, stdout);
    fwrite(rgb, w * h * 3, 1, stdout);
    fflush(stdout);
}

// Feed NAL unit to decoder
static void feed_nal(const uint8_t *nal, int len, int64_t pts_val) {
    if (!session || !nal || len == 0) return;

    // Create CMBlockBuffer
    CMBlockBufferRef blockBuf = NULL;
    OSStatus st = CMBlockBufferCreateWithMemoryBlock(
        kCFAllocatorDefault, (void *)nal, len, kCFAllocatorNull,
        NULL, 0, len, 0, &blockBuf);
    if (st != noErr) return;

    // Create CMSampleBuffer
    CMSampleBufferRef sampleBuf = NULL;
    CMSampleTimingInfo timing = {
        .duration = CMTimeMake(1, 24),
        .presentationTimeStamp = CMTimeMake(pts_val, 24),
        .decodeTimeStamp = kCMTimeInvalid
    };

    st = CMSampleBufferCreateReady(
        kCFAllocatorDefault, blockBuf, fmtDesc, 1, 1,
        &timing, 0, NULL, &sampleBuf);
    CFRelease(blockBuf);
    if (st != noErr) return;

    // Decode
    VTDecodeFrameFlags df = 0;
    VTDecodeInfoFlags info = 0;
    st = VTDecompressionSessionDecodeFrame(
        session, sampleBuf, df, NULL, &info);
    CFRelease(sampleBuf);
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "Usage: vt_decode <input.264>\n"); return 1; }

    // Open input file
    int fd = open(argv[1], O_RDONLY);
    if (fd < 0) { perror("open"); return 1; }

    // Read entire file (for growing files, we'll loop)
    uint8_t buf[16*1024*1024];  // 16MB max per pass
    ssize_t total = 0;
    while (1) {
        ssize_t n = read(fd, buf + total, sizeof(buf) - total - 1);
        if (n <= 0) break;
        total += n;
    }
    close(fd);

    if (total < 4) return 0;

    // Find SPS and PPS
    uint8_t *sps = NULL, *pps = NULL;
    int sps_len = 0, pps_len = 0;
    for (int i = 0; i < total - 4; i++) {
        if (buf[i] == 0 && buf[i+1] == 0 && buf[i+2] == 0 && buf[i+3] == 1) {
            int nal_type = buf[i+4] & 0x1F;
            int start = i + 4;
            int end = total;
            for (int j = start; j < total - 3; j++) {
                if (buf[j]==0 && buf[j+1]==0 && buf[j+2]==0 && buf[j+3]==1) {
                    end = j; break;
                }
            }
            if (nal_type == 7) { sps = buf + start; sps_len = end - start; }
            if (nal_type == 8) { pps = buf + start; pps_len = end - start; }
            i = end - 1;
        }
    }

    if (!sps || !pps) { fprintf(stderr, "No SPS/PPS found\n"); return 1; }

    // Create format description
    const uint8_t *param_ptrs[] = {sps, pps};
    size_t param_sizes[] = {sps_len, pps_len};
    OSStatus st = CMVideoFormatDescriptionCreateFromH264ParameterSets(
        kCFAllocatorDefault, 2, param_ptrs, param_sizes, 4, &fmtDesc);
    if (st != noErr) { fprintf(stderr, "CMVideoFormatDescription failed: %d\n", st); return 1; }

    // Get dimensions
    CMVideoDimensions dims = CMVideoFormatDescriptionGetDimensions(fmtDesc);
    width = dims.width; height = dims.height;

    // Create decompression session
    VTDecompressionOutputCallbackRecord cb = { decode_callback, NULL };

    // Pixel buffer attributes: request BGRA output
    CFNumberRef px_fmt = CFNumberCreate(kCFAllocatorDefault, kCFNumberSInt32Type,
        (int[]){kCVPixelFormatType_32BGRA});
    CFNumberRef px_w = CFNumberCreate(kCFAllocatorDefault, kCFNumberIntType, &width);
    CFNumberRef px_h = CFNumberCreate(kCFAllocatorDefault, kCFNumberIntType, &height);
    const void *keys[] = {
        kCVPixelBufferPixelFormatTypeKey,
        kCVPixelBufferWidthKey,
        kCVPixelBufferHeightKey
    };
    const void *vals[] = {px_fmt, px_w, px_h};
    CFDictionaryRef px_attrs = CFDictionaryCreate(
        kCFAllocatorDefault, keys, vals, 3,
        &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);

    st = VTDecompressionSessionCreate(
        kCFAllocatorDefault, fmtDesc, NULL, px_attrs, &cb, &session);
    CFRelease(px_attrs); CFRelease(px_fmt); CFRelease(px_w); CFRelease(px_h);
    if (st != noErr) { fprintf(stderr, "VTDecompressionSessionCreate failed: %d\n", st); return 1; }

    // Feed all NAL units
    int64_t pts = 0;
    for (int i = 0; i < total - 4; i++) {
        if (buf[i]==0 && buf[i+1]==0 && buf[i+2]==0 && buf[i+3]==1) {
            int nal_start = i + 4;
            int nal_end = total;
            for (int j = nal_start; j < total - 3; j++) {
                if (buf[j]==0 && buf[j+1]==0 && buf[j+2]==0 && buf[j+3]==1) {
                    nal_end = j; break;
                }
            }
            int nal_type = buf[nal_start] & 0x1F;
            if (nal_type == 1 || nal_type == 5) {  // non-IDR or IDR
                // Feed accumulated NALs for this frame (SPS+PPS+slice)
                feed_nal(sps, sps_len, pts);
                feed_nal(pps, pps_len, pts);
                // Also feed preceding SEI if present
                feed_nal(buf + nal_start, nal_end - nal_start, pts);
                pts++;
            }
            i = nal_end - 1;
        }
    }

    // Flush
    VTDecompressionSessionWaitForAsynchronousFrames(session);
    VTDecompressionSessionFinishDelayedFrames(session);

    // Cleanup
    VTDecompressionSessionInvalidate(session);
    CFRelease(session);
    CFRelease(fmtDesc);

    return 0;
}
