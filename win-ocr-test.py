import asyncio, io
from PIL import Image, ImageDraw, ImageFont
from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder, SoftwareBitmap
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

async def pil_to_software_bitmap(img) -> SoftwareBitmap:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream) # type: ignore
    writer.write_bytes(buf.getvalue()) # type: ignore
    await writer.store_async()
    await writer.flush_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream) # type: ignore
    return await decoder.get_software_bitmap_async()

async def test_bbox() -> None:
    img = Image.new("RGB", (500, 170), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
    draw.text((20, 60), "Hello World test 123", fill="black", font=font)

    bitmap = await pil_to_software_bitmap(img)
    engine = OcrEngine.try_create_from_language(Language("en"))
    if engine is None:
        print("OCR engine not available.")
        return
    result = await engine.recognize_async(bitmap)

    # Draw bounding boxes over original image
    overlay = img.copy()
    draw_out = ImageDraw.Draw(overlay)

    if not result.lines:
        print("No text recognized.")
        return

    for line in result.lines:
        if not line.words: continue
        for word in line.words:
            r = word.bounding_rect
            print(f"word='{word.text}' x={r.x:.1f} y={r.y:.1f} w={r.width:.1f} h={r.height:.1f}")
            draw_out.rectangle(
                [r.x, r.y, r.x + r.width, r.y + r.height],
                outline="red", width=2
            )

    overlay.save("bbox_test_output.png")
    print("\nSaved bbox_test_output.png — open it to verify boxes align with words")

asyncio.run(test_bbox())
