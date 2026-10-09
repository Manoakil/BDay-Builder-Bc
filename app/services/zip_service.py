import shutil
from pathlib import Path

def create_zip_package(source_dir: Path, output_path: Path):
    """
    Compresses the source_dir into a zip file at output_path.
    """
    # shutil.make_archive automatically adds .zip to the base_name
    base_name = str(output_path.with_suffix(''))
    shutil.make_archive(
        base_name=base_name,
        format='zip',
        root_dir=source_dir
    )
