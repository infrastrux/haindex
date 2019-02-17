# -*- coding: UTF-8 -*-
from readme_renderer import markdown, rst, txt


class ReadmeRenderer(object):
    RENDER_ENGINES = {
        '': rst,
        '.txt': txt,
        '.rst': rst,
        '.md': markdown,
    }

    def get_html(self, content, extension=None):
        # get renderer for file extension
        renderer = self.RENDER_ENGINES.get(extension, None)
        if not renderer:
            renderer = self.RENDER_ENGINES['']

        # render content and fall back to txt variant if rendering failed
        rendered = renderer.render(content)
        if rendered is None:
            rendered = txt.render(content)

        return rendered
