Screenshot reading (OCR) runs in the visitor's browser. These files are copied unchanged from npm:

  tesseract.min.js, worker.min.js   tesseract.js 7.0.0        (Apache-2.0, see LICENSE-tesseract.js.txt)
  core/*.wasm.js                    tesseract.js-core 7.0.0   (Apache-2.0, see LICENSE-tesseract.js-core.txt)
  lang/*.traineddata.gz             @tesseract.js-data eng, hin, mar, mal, folder 4.0.0_best_int (Tesseract language data, Apache-2.0)

Three core files are kept because the browser picks the fastest one its CPU supports.
They are served from this site, so a screenshot is never sent to a third party.
To update: install a newer tesseract.js with npm and copy the same files again, then re-test with a few images.
