"""
Layout helpers for the Streamlit frontend.

Streamlit closes the HTML of every ``st.markdown`` call independently, so the
common pattern of opening a ``<div class="content-card">`` in one call and
closing it in another renders an *empty* card box with the real content (charts,
tables, columns) falling outside it. ``card()`` wraps a real Streamlit container
(which can hold child widgets) and is styled to look like ``.content-card``.
"""

from __future__ import annotations

from contextlib import contextmanager

import streamlit as st


@contextmanager
def card(title: str | None = None):
    """A bordered container styled like ``.content-card`` that can hold widgets.

    Usage::

        with card("Theme Distribution"):
            st.plotly_chart(fig, use_container_width=True)
    """
    with st.container(border=True):
        if title:
            st.markdown(
                f'<div class="card-title">{title}</div>',
                unsafe_allow_html=True,
            )
        yield


def exec_summary_text(note: dict) -> str:
    """Build a clean, prose executive summary from the structured note.

    The raw ``body_markdown`` is entirely headers/bullets/quotes, so naive
    "prose extraction" leaves nothing and the UI ends up showing literal
    markdown (``#``, ``*``, ``**``). Instead, synthesise a readable paragraph
    from the structured ``top_themes`` summaries.
    """
    top_themes = note.get("top_themes", [])
    sentences: list[str] = []
    for theme in top_themes[:3]:
        name = (theme.get("name") or "").strip()
        summary = (theme.get("summary") or "").strip().rstrip(".")
        if name and summary:
            sentences.append(f"{name}: {summary}.")
        elif summary:
            sentences.append(f"{summary}.")
    if sentences:
        return " ".join(sentences)
    return "AI-generated weekly summary of App Store and Play Store reviews."
