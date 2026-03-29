"""ZIP 包内条目名去重（避免同名覆盖或错误重命名）。"""

import os


def allocate_unique_zip_arcname(used_names: set, arcname: str) -> str:
    """在 used_names 中登记并返回一个不重复的 arcname。

    若与已有条目冲突，则在扩展名前追加 _2、_3……（例如 a/b.pdf -> a/b_2.pdf）。
    """
    if arcname is None:
        arcname = "file"
    else:
        arcname = str(arcname).strip()
        if not arcname:
            arcname = "file"
    original = arcname
    candidate = arcname
    counter = 1
    while candidate in used_names:
        base, ext = os.path.splitext(original)
        counter += 1
        candidate = f"{base}_{counter}{ext}"
    used_names.add(candidate)
    return candidate
