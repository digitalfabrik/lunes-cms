"""
Tests for marking a stored image as AI-generated.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from lunes_cms.cmsv2.services.image_marking import is_marked, mark_image


def _white_webp(path: Path, size: tuple[int, int] = (1024, 1024)) -> None:
    Image.new("RGB", size, "white").save(path, format="WEBP")


def _mark(source: Path) -> Path:
    target = source.with_name("marked.webp")
    mark_image(str(source), str(target))
    return target


def test_pastes_the_label_into_the_bottom_right_corner(tmp_path: Path) -> None:
    source = tmp_path / "image.webp"
    _white_webp(source)

    target = _mark(source)

    with Image.open(target) as image:
        assert image.size == (1024, 1024)
        rgb = image.convert("RGB")
    assert rgb.getpixel((10, 10)) == (255, 255, 255)
    assert sum(rgb.getpixel((800, 974))) < 100
    assert rgb.getpixel((512, 512)) == (255, 255, 255)


def test_embeds_the_digital_source_type_and_leaves_the_source_alone(
    tmp_path: Path,
) -> None:
    source = tmp_path / "image.webp"
    _white_webp(source)
    before = source.read_bytes()

    target = _mark(source)

    assert is_marked(target)
    assert not is_marked(source)
    assert source.read_bytes() == before


def test_keeps_the_file_a_webp_without_alpha(tmp_path: Path) -> None:
    source = tmp_path / "image.webp"
    _white_webp(source)

    with Image.open(_mark(source)) as image:
        assert image.format == "WEBP"
        assert image.mode == "RGB"


def test_leaves_no_temporary_file_behind(tmp_path: Path) -> None:
    source = tmp_path / "image.webp"
    _white_webp(source)

    _mark(source)

    assert sorted(p.name for p in tmp_path.iterdir()) == ["image.webp", "marked.webp"]


def test_does_not_write_a_marked_image_again(tmp_path: Path) -> None:
    source = tmp_path / "image.webp"
    _white_webp(source)
    marked = _mark(source)
    again = tmp_path / "again.webp"

    assert mark_image(str(marked), str(again)) is False
    assert not again.exists()


def test_keeps_the_transparency_of_an_image_with_alpha(tmp_path: Path) -> None:
    source = tmp_path / "image.webp"
    Image.new("RGBA", (1024, 1024), (255, 255, 255, 0)).save(source, format="WEBP")

    with Image.open(_mark(source)) as image:
        assert image.mode == "RGBA"
        assert image.convert("RGBA").getpixel((10, 10))[3] == 0


def test_gives_the_target_the_permissions_of_the_source(tmp_path: Path) -> None:
    source = tmp_path / "image.webp"
    _white_webp(source)
    source.chmod(0o640)

    target = _mark(source)

    assert target.stat().st_mode & 0o777 == 0o640
