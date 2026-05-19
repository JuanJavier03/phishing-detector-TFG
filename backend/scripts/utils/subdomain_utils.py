from __future__ import annotations

"""
Proporciona utilidades pequenas y puras para normalizar y contar etiquetas de subdominio.
"""

from typing import List, Optional


def _strip_leading_www(labels: List[str]) -> List[str]:
    if labels and labels[0].lower() == "www":
        return labels[1:]
    return labels


def subdomain_labels(subdomain: Optional[str]) -> List[str]:
    """
    Split a subdomain string into labels, excluding empty labels and
    dropping "www" only when it is the first label.

    Examples:
      - "www" -> []
      - "www.mail" -> ["mail"]
      - "a.www" -> ["a", "www"]
      - "a.www.b" -> ["a", "www", "b"]
    """

    if not subdomain or not isinstance(subdomain, str):
        return []
    labels = [p.strip() for p in subdomain.split(".") if p and p.strip()]
    return _strip_leading_www(labels)


def normalize_subdomain(subdomain: Optional[str]) -> Optional[str]:
    """
    Normalize a subdomain by stripping only a leading "www" label.
    Returns None when no labels remain.
    """

    labels = subdomain_labels(subdomain)
    return ".".join(labels) or None


def count_subdomain_labels(subdomain: Optional[str]) -> int:
    """
    Count subdomain labels, excluding only a leading "www".
    """

    return len(subdomain_labels(subdomain))

def count_host_labels_without_suffix(
    subdomain: Optional[str],
    registrable_label: Optional[str],
) -> int:
    """
    Count only real subdomain labels, excluding a leading "www" and the public suffix/TLD.

    Examples:
      - ("pepe", "google") -> 1  for pepe.google.com
      - ("www", "google") -> 0   for www.google.com
      - ("www.mail", "google") -> 1 for www.mail.google.com
      - ("a.www", "google") -> 2 for a.www.google.com
      - (None, "google") -> 0    for google.com
      - (None, None) -> 0
    """

    _ = registrable_label
    return len(subdomain_labels(subdomain))


__all__ = [
    "subdomain_labels",
    "normalize_subdomain",
    "count_subdomain_labels",
    "count_host_labels_without_suffix",
]
