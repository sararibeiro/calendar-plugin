from gi.repository import Gtk, Gdk
import cairo
import datetime

from week import Week
from view import ViewBase
from drawing import Header, Background, HEADER_SIZE
from drawtask import DrawTask, TASK_HEIGHT


class WeekView(ViewBase, Gtk.DrawingArea):
    def __init__(self, parent, requester, numdays=7):
        super(WeekView, self).__init__(parent, requester)
        super(Gtk.DrawingArea, self).__init__()

        self.header = Header()
        self.background = Background()

        self.week = Week()
        self.day_width = None
        self.today_column = None
        self.numdays = numdays
        self.min_day_width = 60
        self.show_today()
        self.compute_size()

        self.connect("draw", self.draw)
        self.connect("size-allocate", self.on_size_allocate)

        # drag-and-drop support
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK
                        | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.BUTTON1_MOTION_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("button-press-event", self.dnd_start)
        self.connect("motion-notify-event", self.motion_notify)
        self.connect("button-release-event", self.dnd_stop)
        self.drag_offset = None
        self.drag_action = None
        self.drag = None

    def first_day(self):
        """ Returns the first day of the view being displayed """
        return self.week.start_date

    def last_day(self):
        """ Returns the last day of the view being displayed """
        return self.week.end_date

    def set_day_width(self, day_width):
        """ Sets the width of the column that each day will be drawn. """
        self.day_width = day_width

    def show_today(self):
        """
        Shows the range of dates in the current view with the date
        corresponding to today among it.
        """
        self.week.week_containing_day(datetime.date.today())
        self.update()

    def compute_size(self):
        """ Computes and requests the size needed to draw everything. """
        width = self.min_day_width*self.numdays
        height = TASK_HEIGHT*len(self.tasks)+HEADER_SIZE
        self.set_size_request(width, height)

    def set_week_from(self, start):
        """
        Sets the week to be shown, starting on @start.

        @param start: must be a datetime object, first day to be shown.
        """
        self.week.set_week_starting_on(start)

    def update_header(self):
        """
        Update the header label of the days to be drawn.
        """
        days = self.week.label("%m/%d %a")
        self.header.set_days([(x.split()[0], x.split()[1]) for x in days])

    def update_tasks(self, tasks=None):
        """
        Updates the tasks to be drawn

        @param tasks: a Task list, containing the tasks to be drawn.
         If none is given, the tasks will be retrieved from the requester.
        """
        if not tasks:
            tasks = [self.req.get_task(t) for t in self.req.get_tasks_tree()]
        self.tasks = [DrawTask(t) for t in tasks if self.is_in_days_range(t)]

        # clears selected_task if it is not being showed
        if self.selected_task and \
           not self.is_in_days_range(self.get_selected_task()):
            self.unselect_task()

    def update(self):
        """
        Updates the header, the content to be drawn (tasks), recalculates the
        size needed and then redraws everything.
        """
        self.update_header()
        self.today_column = (datetime.date.today() - self.first_day()).days
        self.update_tasks()
        self.compute_size()
        self.queue_draw()

    def next(self, days=None):
        """
        Advances the dates being displayed by a given number of @days.
        If none is given, the default self.numdays will be used. In this case,
        if the actual first_day being shown is not at the beginning of a
        week, it will advance to the beginning of the next one instead
        of advancing @numdays.

        @param days: integer, the number of days to advance.
         If none is given, the default self.numdays will be used.
        """
        if not days:
            days = self.numdays - self.first_day().weekday()
        self.week.adjust(days)
        self.update()

    def previous(self, days=None):
        """
        Regresses the dates being displayed by a given number of @days.
        If none is given, the default self.numdays will be used. In this case,
        if the actual first_day being shown is not at the beginning of a
        week, it will go back to the beginning of it instead
        of going back @numdays.

        @param days: integer, the number of days to go back.
         If none is given, the default self.numdays will be used.
        """
        if not days:
            days = self.first_day().weekday() or self.numdays
        self.week.adjust(-days)
        self.update()

    def on_size_allocate(self, widget=None, event=None):
        """ Calculates new day_width when window is resized """
        rect = self.get_allocation()
        self.day_width = self.min_day_width
        if self.min_day_width * self.numdays < rect.width:
            self.day_width = rect.width / float(self.numdays)
        self.set_day_width(self.day_width)

    def identify_pointed_object(self, event, clicked=False):
        """
        Identify the object inside drawing area that is being pointed by the
        mouse. Also points out which mouse cursor should be used in result.

        @param event: a Gdk event
        @param clicked: bool, indicates whether or not the user clicked on the
        object being pointed
        """
        const = 10
        cursor = Gdk.Cursor.new(Gdk.CursorType.ARROW)
        for task in self.tasks:
            (x, y, w, h) = task.get_position()
            if not y < event.y < (y + h):
                continue
            if x <= event.x <= x + const:
                self.drag_action = "expand_left"
                cursor = Gdk.Cursor.new(Gdk.CursorType.LEFT_SIDE)
            elif (x + w) - const <= event.x <= (x + w):
                self.drag_action = "expand_right"
                cursor = Gdk.Cursor.new(Gdk.CursorType.RIGHT_SIDE)
            elif x <= event.x <= (x + w):
                self.drag_action = "move"
                if clicked:
                    cursor = Gdk.Cursor.new(Gdk.CursorType.FLEUR)
            else:
                continue
            return task, cursor
        return None, cursor

    def dnd_start(self, widget, event):
        """ User clicked the mouse button, starting drag and drop """
        # find which task was clicked, if any
        (self.selected_task, cursor) = self.identify_pointed_object(
            event, clicked=True)

        if self.selected_task:
            # double-click opens task to edit
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                self.par.on_edit_clicked()
                self.unselect_task()
                return
            self.drag = True
            widget.get_window().set_cursor(cursor)
            task = self.selected_task.task
            start = (task.get_start_date().date() - self.first_day()).days
            end = (task.get_due_date().date() - self.first_day()).days + 1
            duration = end - start

            offset = (start * self.day_width) - event.x
            # offset_y = HEADER_SIZE + pos * TASK_HEIGHT - event.y
            if self.drag_action == "expand_right":
                offset += duration * self.day_width
            self.drag_offset = offset

            self.queue_draw()

    def motion_notify(self, widget, event):
        """ User moved mouse over widget """
        if self.selected_task and self.drag:  # a task was clicked
            task = self.selected_task.task
            start_date = task.get_start_date().date()
            end_date = task.get_due_date().date()
            duration = (end_date - start_date).days

            offset = self.drag_offset
            event_x = event.x + offset
            # event_y = event.y

            weekday = int(event_x / self.day_width)
            day = self.first_day() + datetime.timedelta(weekday)

            if self.drag_action == "expand_left":
                diff = start_date - day
                new_start_day = start_date - diff
                if new_start_day <= end_date:
                    task.set_start_date(new_start_day)
                pass

            elif self.drag_action == "expand_right":
                diff = end_date - day
                new_due_day = end_date - diff
                if new_due_day >= start_date:
                    task.set_due_date(new_due_day)
                pass

            else:
                new_start_day = self.first_day() + \
                    datetime.timedelta(days=weekday)
                new_due_day = new_start_day + datetime.timedelta(days=duration)
                task.set_start_date(new_start_day)
                task.set_due_date(new_due_day)

            self.queue_draw()

        else:  # mouse hover
            (t_id, cursor) = self.identify_pointed_object(event)
            widget.get_window().set_cursor(cursor)

    def dnd_stop(self, widget, event):
        """
        User released a button, stopping drag and drop.
        Selected task, if any, will still have the focus.
        """
        # user didn't click on a task - redraw to 'unselect' task
        if not self.selected_task:
            self.drag = None
            self.queue_draw()
            return

        rect = self.get_allocation()
        if not HEADER_SIZE < event.y < rect.height:
            # do something in the future
            pass
        else:
            event_x = event.x + self.drag_offset
            # event_y = event.y
            weekday = int(event_x / self.day_width)

            task = self.selected_task.task
            start = task.get_start_date().date()
            end = task.get_due_date().date()
            duration = (end - start).days

            new_start_day = self.first_day() + datetime.timedelta(days=weekday)
            if self.drag_action == "expand_right":
                new_start_day = task.get_start_date().date()
            new_due_day = new_start_day + datetime.timedelta(days=duration)

            if not self.drag_action == "expand_right" \
               and new_start_day <= end:
                task.set_start_date(new_start_day)
            if not self.drag_action == "expand_left" \
               and new_due_day >= start:
                task.set_due_date(new_due_day)

        widget.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.ARROW))
        self.drag_offset = None
        self.drag = None
        # self.selected_task = None
        self.queue_draw()

    def draw(self, widget, ctx):
        """ Draws everything inside the DrawingArea """
        ctx.set_line_width(0.8)
        ctx.select_font_face(self.FONT, cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(12)

        self.background.set_column_width(self.day_width)
        self.background.draw(ctx, self.get_allocation(),
                             highlight_col=self.today_column)

        # printing header
        self.header.set_day_width(self.day_width)
        ctx.save()
        ctx.rectangle(0, 0, self.get_allocation().width, HEADER_SIZE)
        ctx.clip()
        self.header.draw(ctx)
        ctx.restore()

        # drawing all tasks
        for pos, drawtask in enumerate(self.tasks):
            if self.selected_task \
               and self.selected_task.get_id() == drawtask.get_id():
                selected = True
            else:
                selected = False
            drawtask.set_day_width(self.day_width)
            drawtask.draw(ctx, pos, self.first_day(), self.last_day(),
                          selected)


class TwoWeeksView(WeekView):
    def __init__(self, parent, requester, numdays=14):
        super(TwoWeeksView, self).__init__(parent, requester)
        self.numdays = numdays
        self.min_day_width = 50
        self.show_today()
        self.compute_size()


class MonthView(WeekView):
    def __init__(self, parent, requester, numdays=31):
        super(MonthView, self).__init__(parent, requester)
        self.numdays = numdays
        self.min_day_width = 40
        self.show_today()
        self.compute_size()
