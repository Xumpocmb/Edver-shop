import shutil
import tempfile
from io import BytesIO
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.template import Context, Template
from django.test import TestCase, override_settings
from PIL import Image

from app_catalog.models import Category, Product, ProductImage, ProductVariant
from app_home.models import Slide
from app_media import processing
from app_media.payload import variant_payload

MEDIA_ROOT = tempfile.mkdtemp(prefix="app-media-tests-")


def make_image(size=(2400, 1600), fmt="JPEG", mode="RGB"):
    buffer = BytesIO()
    color = (200, 30, 60) if mode == "RGB" else (200, 30, 60, 128)
    Image.new(mode, size, color).save(buffer, fmt)
    return SimpleUploadedFile(f"{uuid4().hex}.{fmt.lower()}", buffer.getvalue(), "image/jpeg")


class ImageTestCase(TestCase):
    """Общий хелпер: временный MEDIA_ROOT и уникальные имена файлов."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def save_image(self, instance, field_name="image", **kwargs):
        extension = kwargs.get("fmt", "jpg").lower()
        getattr(instance, field_name).save(
            f"{uuid4().hex}.{extension}", make_image(**kwargs), save=True
        )
        return getattr(instance, field_name)

    @staticmethod
    def stem_of(field_file):
        return field_file.name.rsplit(".", 1)[0].rsplit("/", 1)[-1]


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class GenerateDerivativesTests(ImageTestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Сумки", slug="sumki")
        self.file = self.save_image(self.category)
        self.stem = self.stem_of(self.file)

    def test_generates_derivatives_on_save(self):
        storage = self.file.storage
        for width in (320, 640, 1200, 2000):
            self.assertTrue(storage.exists(f"thumbs/categories/{self.stem}_{width}.jpg"))
            self.assertTrue(storage.exists(f"thumbs/categories/{self.stem}_{width}.webp"))

    def test_source_is_not_replaced(self):
        with Image.open(self.file.storage.open(self.file.name)) as image:
            self.assertEqual(image.size, (2400, 1600))

    def test_derivatives_are_scaled_and_not_enlarged(self):
        storage = self.file.storage
        with Image.open(storage.open(f"thumbs/categories/{self.stem}_320.jpg")) as small:
            self.assertEqual(small.size, (320, 213))
        with Image.open(storage.open(f"thumbs/categories/{self.stem}_320.webp")) as webp:
            self.assertEqual(webp.format, "WEBP")
            self.assertEqual(webp.size, (320, 213))

    def test_small_source_is_not_enlarged(self):
        other = Category.objects.create(name="Кошельки", slug="koshelki")
        file = self.save_image(other, size=(400, 300))
        stem = self.stem_of(file)
        self.assertTrue(file.storage.exists(f"thumbs/categories/{stem}_320.jpg"))
        self.assertFalse(file.storage.exists(f"thumbs/categories/{stem}_640.jpg"))

    def test_transparent_source_falls_back_to_png(self):
        other = Category.objects.create(name="Аксессуары", slug="aksessuary")
        file = self.save_image(other, fmt="png", mode="RGBA")
        stem = self.stem_of(file)
        self.assertTrue(file.storage.exists(f"thumbs/categories/{stem}_640.png"))
        self.assertTrue(file.storage.exists(f"thumbs/categories/{stem}_640.webp"))
        self.assertFalse(file.storage.exists(f"thumbs/categories/{stem}_640.jpg"))

    def test_svg_is_left_untouched(self):
        other = Category.objects.create(name="Рюкзаки", slug="ryukzaki")
        svg = SimpleUploadedFile("logo.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>', "image/svg+xml")
        other.image.save("logo.svg", svg, save=True)
        storage = other.image.storage
        self.assertFalse(storage.exists("thumbs/categories/logo_320.jpg"))
        self.assertFalse(storage.exists("thumbs/categories/logo_320.webp"))
        data = processing.describe(other.image, "product")
        self.assertEqual(data["src"], other.image.url)
        self.assertEqual(data["srcset"], "")

    def test_existing_derivatives_are_not_rebuilt(self):
        self.assertFalse(processing.generate(self.file, "product"))
        self.assertTrue(processing.generate(self.file, "product", force=True))

    def test_files_removed_with_record(self):
        storage = self.file.storage
        self.assertTrue(storage.exists(f"thumbs/categories/{self.stem}_320.webp"))
        self.category.delete()
        self.assertFalse(storage.exists(f"thumbs/categories/{self.stem}_320.webp"))
        self.assertFalse(storage.exists(f"thumbs/categories/{self.stem}_2000.webp"))
        self.assertFalse(storage.exists(self.file.name))

    def test_original_kept_while_another_record_shares_it(self):
        other = Category.objects.create(name="Кошельки", slug="koshelki")
        other.image.name = self.file.name
        other.save()

        self.category.delete()

        self.assertTrue(self.file.storage.exists(self.file.name))
        self.assertTrue(self.file.storage.exists(f"thumbs/categories/{self.stem}_320.webp"))

    def test_record_without_file_is_deleted(self):
        empty = Category.objects.create(name="Ремни", slug="remni")

        empty.delete()

        self.assertFalse(Category.objects.filter(slug="remni").exists())

    def test_describe_reports_original_before_generation(self):
        fresh = Category.objects.create(name="Ремни", slug="remni")
        fresh.image.name = "categories/remen.jpg"
        data = processing.describe(fresh.image, "product")
        self.assertEqual(data["src"], "/media/categories/remen.jpg")
        self.assertEqual(data["srcset"], "")
        self.assertEqual(data["webp"], "")

    def test_describe_lists_existing_derivatives(self):
        data = processing.describe(self.file, "product")
        self.assertIn(f"thumbs/categories/{self.stem}_320.jpg 320w", data["srcset"])
        self.assertIn(f"thumbs/categories/{self.stem}_2000.webp 2000w", data["webp"])
        self.assertTrue(data["src"].endswith(f"thumbs/categories/{self.stem}_2000.jpg"))
        self.assertEqual(len(data["variants"]), 4)

    def test_slide_profile(self):
        slide = Slide.objects.create(title="Акция", bg="#123456")
        file = self.save_image(slide, size=(2400, 1200))
        stem = self.stem_of(file)
        self.assertTrue(file.storage.exists(f"thumbs/slides/{stem}_768.webp"))
        data = processing.describe(file, "slide")
        self.assertIn(f"thumbs/slides/{stem}_768.webp 768w", data["webp"])
        self.assertNotIn("320w", data["srcset"])

    def test_rebuild_command(self):
        slide = Slide.objects.create(title="Акция", bg="#123456")
        file = self.save_image(slide, size=(2400, 1200))
        stem = self.stem_of(file)
        storage = file.storage
        storage.delete(f"thumbs/slides/{stem}_768.webp")
        storage.delete(f"thumbs/categories/{self.stem}_320.webp")
        self.assertFalse(storage.exists(f"thumbs/slides/{stem}_768.webp"))

        call_command("rebuild_image_derivatives", verbosity=0)

        self.assertTrue(storage.exists(f"thumbs/slides/{stem}_768.webp"))
        self.assertTrue(storage.exists(f"thumbs/categories/{self.stem}_320.webp"))


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DeleteRecordFilesTests(ImageTestCase):
    """Удаление товара должно уносить с диска фото его вариантов."""

    def setUp(self):
        self.category = Category.objects.create(name="Сумки", slug="sumki")
        self.product = Product.objects.create(
            name="Сумка", slug="sumka", category=self.category
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, color="красный", price="100.00"
        )
        self.files = [
            self.save_image(self.variant.images.create(alt=alt), size=(900, 600)).name
            for alt in ("Красная", "Вид сбоку")
        ]
        # Проверки «файла нет» осмысленны, только если до удаления он был.
        for name in self.files:
            self.assert_present(self.category.image.storage, name)

    def assert_present(self, storage, name):
        """Оригинал и превью на диске есть.

        Проверяем только 320: generate() не делает копии шире исходника, а 320
        существует у любой загруженной фотографии.
        """
        self.assertTrue(storage.exists(name), name)
        self.assertTrue(storage.exists(processing.thumb_name(name, 320, "jpg")), name)

    def assert_missing(self, storage, name):
        """Оригинала и всех его превью на диске нет."""
        self.assertFalse(storage.exists(name), name)
        for width in processing.PROFILES["product"]:
            for fmt in (*processing.FALLBACK_FORMATS, processing.WEBP):
                self.assertFalse(storage.exists(processing.thumb_name(name, width, fmt)), name)

    def test_product_delete_removes_variant_photos(self):
        storage = self.category.image.storage

        self.product.delete()

        for name in self.files:
            self.assert_missing(storage, name)

    def test_variant_delete_removes_only_its_photos(self):
        other = ProductVariant.objects.create(
            product=self.product, color="синий", price="110.00"
        )
        keep = self.save_image(other.images.create(alt="Синяя"))

        self.variant.delete()

        self.assert_missing(keep.storage, self.files[0])
        self.assertTrue(keep.storage.exists(keep.name))

    def test_photo_delete_removes_its_files(self):
        image = self.variant.images.first()

        image.delete()

        self.assert_missing(image.image.storage, self.files[0])


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ReplaceImageFilesTests(ImageTestCase):
    """Замена фото должна уносить прежний файл, а нетронутое — не трогать."""

    def setUp(self):
        self.category = Category.objects.create(name="Сумки", slug="sumki")
        self.product = Product.objects.create(
            name="Сумка", slug="sumka", category=self.category
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, color="красный", price="100.00"
        )
        self.image = self.variant.images.create(alt="Красная")
        self.old_name = self.save_image(self.image, size=(2400, 1600)).name

    def thumb(self, name, width=320, fmt="jpg"):
        return processing.thumb_name(name, width, fmt)

    def test_replace_removes_previous_original_and_thumbs(self):
        storage = self.category.image.storage
        self.assertTrue(storage.exists(self.old_name))

        fresh = self.save_image(self.image, size=(2400, 1600)).name

        self.assertFalse(storage.exists(self.old_name))
        for width in processing.PROFILES["product"]:
            self.assertFalse(storage.exists(self.thumb(self.old_name, width)))
        self.assertTrue(storage.exists(fresh))
        self.assertTrue(storage.exists(self.thumb(fresh, 640)))

    def test_save_without_replacing_keeps_file(self):
        storage = self.category.image.storage

        self.image.alt = "Другое описание"
        self.image.save()

        self.assertTrue(storage.exists(self.old_name))
        self.assertTrue(storage.exists(self.thumb(self.old_name, 640)))

    def test_previous_file_kept_while_another_record_shares_it(self):
        twin = self.variant.images.create(alt="Дубль")
        twin.image.name = self.old_name
        twin.save()
        storage = self.category.image.storage

        self.save_image(self.image, size=(2400, 1600))

        self.assertTrue(storage.exists(self.old_name))
        self.assertTrue(storage.exists(self.thumb(self.old_name, 640)))


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ImageTagTests(ImageTestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Сумки", slug="sumki")
        self.file = self.save_image(self.category)
        self.stem = self.stem_of(self.file)

    def render(self, template, **context):
        return Template("{% load image_tags %}" + template).render(Context(context))

    def test_responsive_image_renders_picture_with_srcset(self):
        html = self.render(
            "{% responsive_image category.image 'product' alt='Сумка' classes='card-img' sizes='(max-width: 640px) 50vw, 240px' %}",
            category=self.category,
        )
        self.assertIn("<picture>", html)
        self.assertIn('type="image/webp"', html)
        self.assertIn(f"{self.stem}_320.webp 320w", html)
        self.assertIn('sizes="(max-width: 640px) 50vw, 240px"', html)
        self.assertIn('loading="lazy"', html)
        self.assertIn('alt="Сумка"', html)
        self.assertIn('class="card-img"', html)

    def test_responsive_image_without_derivatives_is_plain_img(self):
        self.category.image.name = "categories/none.jpg"
        html = self.render(
            "{% responsive_image category.image 'product' alt='' %}", category=self.category
        )
        self.assertNotIn("<picture>", html)
        self.assertIn('src="/media/categories/none.jpg"', html)
        self.assertNotIn("srcset", html)

    def test_slide_background_renders_picture(self):
        slide = Slide.objects.create(title="Акция", bg="#123456")
        file = self.save_image(slide, size=(2400, 1200))
        stem = self.stem_of(file)
        html = self.render("{% slide_background slide %}", slide=slide)
        self.assertIn(f"/media/thumbs/slides/{stem}_768.webp 768w", html)
        self.assertIn('fetchpriority="high"', html)
        self.assertIn('sizes="100vw"', html)

    def test_variant_payload_carries_srcset(self):
        product = Product.objects.create(name="Сумка", slug="sumka", category=self.category)
        variant = ProductVariant.objects.create(product=product, color="красный", price="100.00")
        ProductImage.objects.create(variant=variant, image=self.file)

        image = variant_payload(variant)["images"][0]

        self.assertIn(f"{self.stem}_320.jpg 320w", image["srcset"])
        self.assertIn(f"{self.stem}_320.webp 320w", image["webp"])
        self.assertTrue(image["src"].endswith(f"thumbs/categories/{self.stem}_2000.jpg"))
        self.assertEqual(image["alt"], "Сумка красный")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PageRenderTests(ImageTestCase):
    """Страницы с картинками должны отдавать srcset и не падать."""

    def setUp(self):
        self.category = Category.objects.create(name="Сумки", slug="sumki")
        self.product = Product.objects.create(name="Сумка", slug="sumka", category=self.category)
        self.variant = ProductVariant.objects.create(
            product=self.product, color="красный", price="100.00"
        )
        for alt in ("", "Вторая фотография"):
            self.variant.images.create(image=make_image(size=(900, 600)), alt=alt)
        Slide.objects.create(title="Акция", bg="#123456").image.save(
            f"{uuid4().hex}.jpg", make_image(size=(2400, 1200)), save=True
        )

    def test_catalog_page_uses_srcset(self):
        html = self.client.get("/catalog/").content.decode()
        self.assertIn("sizes=\"(max-width: 640px) 50vw, 240px\"", html)
        self.assertIn("type=\"image/webp\"", html)

    def test_product_page_uses_srcset_and_payload(self):
        html = self.client.get(self.product.get_absolute_url()).content.decode()
        self.assertIn("sizes=\"(max-width: 1080px) 100vw, 600px\"", html)
        self.assertIn("fetchpriority=\"high\"", html)
        self.assertIn('id="gallery-images"', html)
        self.assertIn("gallery-images", html)

    def test_home_slide_picture(self):
        html = self.client.get("/").content.decode()
        self.assertIn("slide-picture", html)
        self.assertIn("sizes=\"100vw\"", html)

