/* Fast YUV420→RGB888 conversion — compiled as shared library.
   Called from Python via ctypes. Handles 640x360 frame in <1ms. */

#include <stdint.h>

void yuv420_to_rgb888(
    const uint8_t *y, const uint8_t *u, const uint8_t *v,
    uint8_t *rgb, int w, int h)
{
    for (int j = 0; j < h; j++) {
        int uv_row = (j / 2) * (w / 2);
        int row_off = j * w * 3;
        for (int i = 0; i < w; i++) {
            int yi = y[j * w + i];
            int ui = u[uv_row + i / 2] - 128;
            int vi = v[uv_row + i / 2] - 128;

            int r = yi + ((1402 * vi) / 1000);
            int g = yi - ((344 * ui + 714 * vi) / 1000);
            int b = yi + ((1772 * ui) / 1000);

            int idx = row_off + i * 3;
            rgb[idx]   = r < 0 ? 0 : (r > 255 ? 255 : r);
            rgb[idx+1] = g < 0 ? 0 : (g > 255 ? 255 : g);
            rgb[idx+2] = b < 0 ? 0 : (b > 255 ? 255 : b);
        }
    }
}
