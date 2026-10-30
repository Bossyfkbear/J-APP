"""Publish finished temporary files without replacing existing user files."""
import errno
import os
from pathlib import Path
import shutil
import tempfile


def publish_file(staged, destination):
    """Prefer atomic hard links; support filesystems without hard-link support.

    Windows fallback copies into a temporary file in the destination directory
    and publishes with non-replacing os.rename; this avoids visible partial
    outputs on Windows filesystems without hard links. On POSIX the fallback
    retains exclusive creation (never overwrite) but can expose partial copies.
    """
    staged, destination = Path(staged), Path(destination)
    try:
        os.link(staged, destination)
        return
    except OSError as exc:
        unsupported = {errno.EXDEV, errno.EPERM, errno.ENOSYS, errno.ENOTSUP,
                       errno.EOPNOTSUPP}
        if exc.errno not in unsupported and getattr(exc, 'winerror', None) not in (1, 50):
            raise
    if os.name == 'nt':
        # Windows os.rename refuses to replace an existing destination. Unlike
        # os.replace, this is no-overwrite and atomic on the same volume.
        # The sibling temporary file remains private until fully flushed.
        if destination.exists():
            raise FileExistsError(destination)
        partial = None
        try:
            with staged.open('rb') as source:
                with tempfile.NamedTemporaryFile(
                    mode='wb', dir=destination.parent,
                    prefix=f'.{destination.name}.', suffix='.partial',
                    delete=False,
                ) as output:
                    partial = Path(output.name)
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                    output.flush()
                    os.fsync(output.fileno())
            os.rename(partial, destination)
        finally:
            if partial is not None:
                partial.unlink(missing_ok=True)
        return
    # POSIX without hardlinks: exclusive create avoids overwriting a file.
    # Open the source first; failure must not create an empty destination.
    with staged.open('rb') as source:
        output = destination.open('xb')
        try:
            with output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
