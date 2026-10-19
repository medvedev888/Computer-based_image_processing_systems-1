import argparse
from pathlib import Path
from statistics import median
from time import perf_counter

from PIL import Image, ImageDraw, ImageFilter, ImageOps


def erode_python(image):
    width, height = image.size
    source = image.load()
    result = Image.new("L", image.size, 0)
    target = result.load()
    for y in range(height):
        for x in range(width):
            minimum = 255
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        value = source[nx, ny]
                        if value < minimum:
                            minimum = value
            target[x, y] = minimum
    return result


def erode_pillow(image):
    padded = ImageOps.expand(image, border=1, fill=255)
    filtered = padded.filter(ImageFilter.MinFilter(3))
    return filtered.crop((1, 1, image.width + 1, image.height + 1))


def measure(function, image, repeats):
    function(image)
    times = []
    for _ in range(repeats):
        start = perf_counter()
        result = function(image)
        times.append(perf_counter() - start)
    return result, median(times)


def save_comparison(images, folder):
    width, height = images[0][1].size
    canvas = Image.new("RGB", (width * len(images), height + 28), "#dddddd")
    draw = ImageDraw.Draw(canvas)
    for index, (label, image) in enumerate(images):
        canvas.paste(image, (index * width, 28))
        draw.text((index * width + 5, 7), label, fill="black")
    canvas.save(folder / "comparison.png")


def parse_args():
    parser = argparse.ArgumentParser(description="Эрозия 3x3: Python и Pillow")
    parser.add_argument("image", type=Path, help="Путь к изображению")
    parser.add_argument("--threshold", type=int, default=128, help="Порог 0..255")
    parser.add_argument("--repeats", type=int, default=5, help="Число замеров")
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    if not 0 <= args.threshold <= 255:
        parser.error("Порог должен быть от 0 до 255")
    if args.repeats < 1:
        parser.error("Нужен хотя бы один замер")
    return args


def main():
    args = parse_args()
    try:
        with Image.open(args.image) as source:
            gray = ImageOps.exif_transpose(source).convert("L")
    except (OSError, ValueError) as error:
        raise SystemExit(f"Не удалось открыть изображение: {error}")
    binary = gray.point(lambda value: 255 if value >= args.threshold else 0)
    native, native_time = measure(erode_python, binary, args.repeats)
    library, library_time = measure(erode_pillow, binary, args.repeats)
    if native.tobytes() != library.tobytes():
        raise RuntimeError("Результаты реализаций не совпали")
    args.output.mkdir(parents=True, exist_ok=True)
    gray.save(args.output / "gray.png")
    binary.save(args.output / "binary.png")
    native.save(args.output / "python.png")
    library.save(args.output / "pillow.png")
    save_comparison([("Binary", binary), ("Python", native), ("Pillow", library)], args.output)
    print(f"Размер: {binary.width}x{binary.height}; порог: {args.threshold}")
    print(f"Медиана {args.repeats} замеров: Python {native_time * 1000:.3f} мс;")
    print(f"Pillow {library_time * 1000:.3f} мс")
    print(f"Ускорение: {native_time / library_time:.2f}x")
    print(f"Результаты совпадают. Изображения: {args.output.resolve()}")


if __name__ == "__main__":
    main()
