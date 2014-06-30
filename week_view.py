from gi.repository import Gtk, Gdk, GObject
import datetime

from week import Week
from drawtask import DrawTask, TASK_HEIGHT
from all_day_tasks import AllDayTasks
from header import Header
from grid import Grid
import utils
from view import ViewBase


class WeekView(ViewBase, Gtk.VBox):
    __string_signal__ = (GObject.SignalFlags.RUN_FIRST, None, (str, ))
    __none_signal__ = (GObject.SignalFlags.RUN_FIRST, None, tuple())
    __gsignals__ = {'on_edit_clicked': __string_signal__,
                    'dates-changed': __none_signal__,
                   }

    def __init__(self, parent, requester, numdays=7):
        super(WeekView, self).__init__(parent, requester)
        super(Gtk.VBox, self).__init__()

        self.numdays = numdays
        self.min_day_width = 60
        self.grid = Grid(1, self.numdays)
        self.week = Week()

        # Header
        self.header = Header()
        self.header.set_size_request(-1, 35)
        self.pack_start(self.header, False, False, 0)

        # Scrolled Window
        self.scroll = Gtk.ScrolledWindow(None, None)
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add_events(Gdk.EventMask.SCROLL_MASK)
        self.scroll.connect("scroll-event", self.on_scroll)
        self.pack_start(self.scroll, True, True, 0)

        # AllDayTasks widget
        self.all_day_tasks = AllDayTasks(self)
        self.scroll.add_with_viewport(self.all_day_tasks)

        #self.show_today()

        # drag-and-drop support
        self.drag_offset = None
        self.drag_action = None
        self.is_dragging = False

        # handle the AllDayTasks DnD events
        self.all_day_tasks.connect("button-press-event", self.dnd_start)
        self.all_day_tasks.connect("motion-notify-event", self.motion_notify)
        self.all_day_tasks.connect("button-release-event", self.dnd_stop)

        self.connect("size-allocate", self.on_size_allocate)

    def on_scroll(self, widget, event):
        """
        Callback function to deal with scrolling the drawing area window.
        If scroll right or left, change the days displayed in the calendar
        view. If scroll up or down, propagates the signal to scroll window
        normally.
        """
        # scroll right
        if event.get_scroll_deltas()[1] > 0:
            self.next(days=1)
        # scroll left
        elif event.get_scroll_deltas()[1] < 0:
            self.previous(days=1)
        # scroll up or down
        else:
            return False  # propagates signal to scroll window normally
        return True

    def unselect_task(self):
        """ Unselects the task that was selected before. """
        self.selected_task = None
        self.all_day_tasks.selected_task = None

    def first_day(self):
        """ Returns the first day of the view being displayed """
        return self.week.start_date

    def last_day(self):
        """ Returns the last day of the view being displayed """
        return self.week.end_date

    def get_day_width(self):
        """ Returns the day/column width in pixels """
        return round(self.all_day_tasks.get_day_width(), 3)

    def show_today(self):
        """
        Shows the range of dates in the current view with the date
        corresponding to today among it.
        """
        self.week.week_containing_day(datetime.date.today())
        self.update()

    def on_size_allocate(self, widget=None, event=None):
        """ Calculates new day_width when window is resized """
        pass

    def compute_size(self):
        """ Computes and requests the size needed to draw everything. """
        width = self.min_day_width * self.numdays
        height = TASK_HEIGHT * self.grid.num_rows
        self.all_day_tasks.set_size_request(width, height)

        # verify if the scrollbar is present, and notifies header of that
        # FIXME: not working when removing one task (but scrollbar continues)
        # if removes task but the scrollbar disappears -> works properly
        alloc = self.all_day_tasks.get_allocation()
        if alloc.height > 1 and height >= alloc.height:
            self.header.set_sidebar_size(15)
        else:
            self.header.set_sidebar_size(0)

    def set_week_from(self, start):
        """
        Sets the week to be shown, starting on @start.

        @param start: must be a datetime object, first day to be shown.
        """
        self.week.set_week_starting_on(start)

    def update_header(self, format="%a %m/%d"):
        """
        Updates the header label of the days to be drawn given a specific
        strftime @format, and then redraws the header. If more than one line is
        wanted to display each labels, the format must separate the content
        inteded for each line by a space.

        @param format: string, must follow the strftime convention.
         Default: "%a %m/%d" - abbrev weekday in first line,
         month/day_of_month as decimal numbers in second line.
        """
        days = self.week.label(format)
        days = [d.split() for d in days]
        self.header.set_labels(days)
        self.header.queue_draw()
        self.emit('dates-changed')

    def set_task_drawing_position(self, dtask):
        """
        Calculates and sets the position of a @dtask.

        @param dtask: a DrawingTask object.
        """
        task = self.req.get_task(dtask.get_id())

        start = max(task.get_start_date().date(), self.first_day())
        end = min(task.get_due_date().date(), self.last_day())
        duration = (end - start).days + 1

        x = utils.date_to_col_coord(start, self.first_day())
        w = duration
        x, y, w, h = self.grid.add_to_grid(x, w, id=dtask.get_label()[4])

        dtask.set_position(x, y, w, h)
        dtask.set_overflowing_L(self.first_day())
        dtask.set_overflowing_R(self.last_day())

    def update_tasks(self):
        """ Updates and redraws everything related to the tasks """
        self.update_drawtasks()
        self.compute_size()
        self.all_day_tasks.queue_draw()

    def update_drawtasks(self, tasks=None):
        """
        Updates the drawtasks and calculates the position of where each one of
        them should be drawn.

        @param tasks: a Task list, containing the tasks to be drawn.
         If none is given, the tasks will be retrieved from the requester.
        """
        if not tasks:
            tasks = [self.req.get_task(t) for t in self.req.get_tasks_tree()]
        self.tasks = [DrawTask(t) for t in tasks if self.is_in_days_range(t)]

        self.grid.clear_rows()
        for t in self.tasks:
            self.set_task_drawing_position(t)
        self.all_day_tasks.set_tasks_to_draw(self.tasks)

        # clears selected_task if it is not being showed
        if self.selected_task and \
           not self.is_in_days_range(self.get_selected_task()):
            self.unselect_task()
        self.all_day_tasks.selected_task = self.selected_task

    def highlight_today_cell(self):
        """ Highlights the cell equivalent to today."""
        row = 0
        col = utils.date_to_col_coord(datetime.date.today(), self.first_day())
        self.all_day_tasks.set_highlight_cell(row, col)
        self.header.set_highlight_cell(0, col)

    def update(self):
        """
        Updates the header, the content to be drawn (tasks), recalculates the
        size needed and then redraws everything.
        """
        self.update_drawtasks()
        self.compute_size()
        self.highlight_today_cell()
        self.update_header()
        self.all_day_tasks.queue_draw()

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

    def dnd_start(self, widget, event):
        """ User clicked the mouse button, starting drag and drop """
        # find which task was clicked, if any
        self.selected_task, self.drag_action, cursor = \
            self.all_day_tasks.identify_pointed_object(event, clicked=True)

        if self.selected_task:
            # double-click opens task to edit
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                GObject.idle_add(self.emit, 'on_edit_clicked', self.selected_task.get_id())
                self.unselect_task()
                return
            self.is_dragging = True
            widget.get_window().set_cursor(cursor)
            task = self.selected_task.task
            start = (task.get_start_date().date() - self.first_day()).days
            end = (task.get_due_date().date() - self.first_day()).days + 1
            duration = end - start

            day_width = self.get_day_width()
            offset = (start * day_width) - event.x
            # offset_y = pos * TASK_HEIGHT - event.y
            if self.drag_action == "expand_right":
                offset += duration * day_width
            self.drag_offset = offset

            self.update_tasks()

    def motion_notify(self, widget, event):
        """ User moved mouse over widget """
        if self.selected_task and self.is_dragging:  # a task was clicked
            task = self.selected_task.task
            start_date = task.get_start_date().date()
            end_date = task.get_due_date().date()
            duration = (end_date - start_date).days

            event_x = round(event.x + self.drag_offset, 3)
            # event_y = event.y

            day_width = self.get_day_width()
            weekday = utils.convert_coordinates_to_col(event_x, day_width)
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

            self.update()

        else:  # mouse hover
            t_id, self.drag_action, cursor = \
                self.all_day_tasks.identify_pointed_object(event)
            widget.get_window().set_cursor(cursor)

    def dnd_stop(self, widget, event):
        """
        User released a button, stopping drag and drop.
        Selected task, if any, will still have the focus.
        """
        # user didn't click on a task - redraw to 'unselect' task
        if not self.selected_task:
            self.is_dragging = False
            self.drag_offset = None
            self.unselect_task()
            self.all_day_tasks.queue_draw()
            return

        event_x = round(event.x + self.drag_offset, 3)
        # event_y = event.y

        day_width = self.get_day_width()
        weekday = utils.convert_coordinates_to_col(event_x, day_width)

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
        self.is_dragging = False
        # self.selected_task = None
        self.update_tasks()
