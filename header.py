from gi.repository import Gtk
from background import Background
import cairo


class Header(Gtk.DrawingArea):
    def __init__(self):
        super(Header, self).__init__()
        self.labels = []
        self.background = Background(1, 7)
        self.sidebar = 0
        self.font = "Courier"
        self.font_size = 12
        self.font_color = (0.35, 0.31, 0.24)
        self.highlight_cell = (None, None)

        self.connect("draw", self.draw)

    def set_sidebar_size(self, size):
        self.sidebar = size

    def set_labels(self, labels):
        self.labels = labels

    def set_font(self, font):
        self.font = font

    def set_font_size(self, size):
        self.font_size = size

    def set_font_color(self, color):
        self.font_color = color

    def set_line_color(self, color):
        self.background.set_line_color(color)

    def set_background_color(self, color):
        self.background.set_background_color(color)

    def get_height(self):
        return self.get_allocation().height

    def get_col_width(self):
        try:
            col_width = (self.get_allocation().width - self.sidebar) \
                / float(len(self.labels))
        except ZeroDivisionError:
            print("List of labels in object Header not initialized!")
            raise
        else:
            return col_width

    def set_highlight_cell(self, row, col):
        if row == 0 and 0 <= col < len(self.labels):
            self.highlight_cell = (row, col)
        else:
            self.highlight_cell = (None, None)

    def draw(self, widget, ctx):
        """
        Draws the header according to the labels.

        @param ctx: a Cairo context
        """
        alloc = self.get_allocation()
        alloc.width -= self.sidebar
        # FIXME: look deeper into why x=5 and y=35 - both should start at 0
        # Whathever is happening has to do with spacing in vbox (glade file)
        # temporary fix:
        alloc.x = 0
        alloc.y = 0

        ctx.set_line_width(0.8)
        row, col = self.highlight_cell
        if row is not None and col is not None:
            # print "header", alloc.x, alloc.y, alloc.width, alloc.height
            self.background.highlight_cell(ctx, row, col, alloc)

        self.background.draw(ctx, alloc, vgrid=False, hgrid=True)

        col_width = self.get_col_width()
        color = self.font_color
        ctx.set_source_rgb(color[0], color[1], color[2])

        ctx.set_font_size(self.font_size)
        ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)

        # FIXME: print dates in one line and weekday in another
        for i in range(0, len(self.labels)):
            (x, y, w, h, dx, dy) = ctx.text_extents(self.labels[i])
            base_x = (i * col_width) - ((w - col_width) / 2.0)
            base_y = self.get_height()/2.0 + h
            ctx.move_to(base_x, base_y)
            ctx.text_path(self.labels[i])
            ctx.stroke()
