from __future__ import annotations

import cappa

from responsaas.cli import Responsaas


def main() -> None:
    cappa.invoke(Responsaas)


if __name__ == "__main__":
    main()
