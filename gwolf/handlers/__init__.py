from gwolf.handlers.pdf import handle_pdf_merge, handle_pdf_compress, handle_pdf_to_img
from gwolf.handlers.image import handle_img_to_pdf, handle_img_compress, handle_img_upscale, handle_img_convert
from gwolf.handlers.docs import handle_word_to_pdf, handle_pdf_to_word
from gwolf.handlers.status import handle_get

POST_ROUTES = {
    "/api/pdf/merge": handle_pdf_merge,
    "/api/pdf/compress": handle_pdf_compress,
    "/api/pdf/to-img": handle_pdf_to_img,
    "/api/img/to-pdf": handle_img_to_pdf,
    "/api/img/compress": handle_img_compress,
    "/api/img/upscale": handle_img_upscale,
    "/api/img/convert": handle_img_convert,
    "/api/word/to-pdf": handle_word_to_pdf,
    "/api/pdf/to-word": handle_pdf_to_word,
}

__all__ = ["POST_ROUTES", "handle_get"]
