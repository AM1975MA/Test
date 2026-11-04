import io
import stat
import unittest
import zipfile
from restore_original_olc14 import validate_zip_members

def archive(names, external_attributes=None):
    f=io.BytesIO()
    with zipfile.ZipFile(f,"w") as z:
        for name in names:
            i=zipfile.ZipInfo(name)
            if external_attributes and name in external_attributes:
                i.external_attr=external_attributes[name]
            z.writestr(i,"file data")
    f.seek(0)
    return zipfile.ZipFile(f)

class RestoreSafety(unittest.TestCase):
    def test_valid_archive(self):
        with archive(["olc14_fitted_ranking_20261101/HEADS_MANIFEST.json"]) as z:
            validate_zip_members(z)

    def test_prevents_zip_slip(self):
        with archive(["../outside/file","good/file"]) as z:
            with self.assertRaises(ValueError):
                validate_zip_members(z)

    def test_rejects_absolute_member(self):
        with archive(["/tmp/suspicious"]) as z:
            with self.assertRaises(ValueError):
                validate_zip_members(z)

    def test_rejects_symlink(self):
        with archive(["link"],{"link":(stat.S_IFLNK|0o777)<<16}) as z:
            with self.assertRaises(ValueError):
                validate_zip_members(z)

if __name__=="__main__":
    unittest.main(verbosity=2)
