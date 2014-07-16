from gi.repository import Gtk, Gdk, GObject
import datetime
import calendar

from week import WeekSpan
from drawtask import DrawTask
from all_day_tasks import AllDayTasks
from header import Header
from grid import Grid
import utils
from view import ViewBase


class MonthView(ViewBase, Gtk.VBox):
    __string_signal__ = (GObject.SignalFlags.RUN_FIRST, None, (str, ))
    __2string_signal__ = (GObject.SignalFlags.RUN_FIRST, None, (str, str,))
    __none_signal__ = (GObject.SignalFlags.RUN_FIRST, None, tuple())
    __gsignals__ = {'on_edit_task': __string_signal__,
                    'on_add_task': __2string_signal__,
                    'dates-changed': __none_signal__,
                    }

    def __init__(self, parent, requester, numdays=7):
        super(MonthView, self).__init__(parent, requester)
        super(Gtk.VBox, self).__init__()

        self.numdays = numdays
        self.min_day_width = 60
        self.min_week_height = 80
        today = datetime.date.today()
        self.numweeks = self.calculate_number_of_weeks(today.year, today.month)

        # Header
        self.header = Header(self.numdays)
        self.header.set_size_request(-1, 35)
        self.pack_start(self.header, False, False, 0)

        # Scrolled Window
        self.scroll = Gtk.ScrolledWindow(None, None)
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        self.scroll.add_events(Gdk.EventMask.SCROLL_MASK)
        self.scroll.connect("scroll-event", self.on_scroll)
        self.pack_start(self.scroll, True, True, 0)

        # AllDayTasks widget
        self.all_day_tasks = AllDayTasks(self, rows=self.numweeks,
                                         cols=self.numdays)
        # self.pack_start(self.all_day_tasks, True, True, 0)
        self.scroll.add_with_viewport(self.all_day_tasks)

        # drag-and-drop support
        self.drag_offset = None
        self.drag_action = None
        self.is_dragging = False

        # handle the AllDayTasks DnD events
        self.all_day_tasks.connect("button-press-event", self.dnd_start)
        self.all_day_tasks.connect("motion-notify-event", self.motion_notify)
        self.all_day_tasks.connect("button-release-event", self.dnd_stop)

    def init_weeks(self, numweeks):
        """
        Initializates the structure needed to manage dates, tasks and task
        positions for each one of the @numweeks weeks of the month.
        Structure self.weeks is a list of size @numweeks, where each position
        manages the dates corresponding to a week, being actually a dictionary
        with entries:
            'grid': contains Grid object.
            'dates': contains WeekSpan object.
            'tasks': is an empty list, will keep track of list of DrawTask.

        @param numweeks: integer, the number of weeks
        """
        self.weeks = []
        for w in range(numweeks):
            week = {}
            week['grid'] = Grid(1, self.numdays)
            week['dates'] = WeekSpan()
            week['tasks'] = []
            self.weeks.append(week)
        self.all_day_tasks.set_num_rows(numweeks)

    def on_scroll(self, widget, event):
        """
        Callback function to deal with scrolling the drawing area window.
        If scroll right or left, change the days displayed in the calendar
        view.
        """
        # scroll right
        if event.get_scroll_deltas()[1] > 0:
            self.next(months=1)
        # scroll left
        elif event.get_scroll_deltas()[1] < 0:
            self.previous(months=1)
        return True

    def unselect_task(self):
        """ Unselects the task that was selected before. """
        self.selected_task = None
        self.all_day_tasks.selected_task = None

    def first_day(self):
        """ Returns the first day of the view being displayed """
        return self.weeks[0]['dates'].start_date

    def last_day(self):
        """ Returns the last day of the view being displayed """
        return self.weeks[-1]['dates'].end_date

    def get_day_width(self):
        """ Returns the day/column width in pixels """
        return round(self.all_day_tasks.get_day_width(), 3)

    def show_today(self):
        """
        Shows the range of dates in the current view with the date
        corresponding to today among it.
        """
        today = datetime.date.today()
        self.update_weeks(today.year, today.month)
        self.update()

    def compute_size(self):
        """ Computes and requests the size needed to draw everything. """
        width = self.min_day_width * self.numdays
        height = self.min_week_height * self.numweeks
        self.all_day_tasks.set_size_request(width, height)

    def calculate_number_of_weeks(self, year, month):
        """
        Calculates the number of weeks the given @month of a @year has.

        @param year: integer, a valid year in the format YYYY.
        @param month: integer, a month (should be between 1 and 12)
        """
        num_days_in_month = calendar.monthrange(year, month)[1]
        first_day = datetime.date(year, month, 1)
        last_day = datetime.date(year, month, num_days_in_month)
        total_weeks = utils.date_to_row_coord(last_day, first_day) + 1
        return total_weeks

    def update_weeks(self, year, month):
        """
        Updates the dates of the weeks of a a specific @month of a @year.
        This will erase the whole self.weeks structure, and then fill the entry
        week['dates'] of each week with the right dates.

        @param year: integer, a valid year in the format YYYY.
        @param month: integer, a month (should be between 1 and 12)
        """
        self.numweeks = self.calculate_number_of_weeks(year, month)
        self.init_weeks(self.numweeks)
        first_day = datetime.date(year, month, 1)
        for i, week in enumerate(self.weeks):
            new_week = WeekSpan()
            day = first_day + datetime.timedelta(days=i*7)
            new_week.week_containing_day(day)
            week['dates'] = new_week

    def update_header(self, format="%A"):
        """
        Updates the header label of the days to be drawn given a specific
        strftime @format, and then redraws the header. If more than one line is
        wanted to display each labels, the format must separate the content
        inteded for each line by a space.

        @param format: string, must follow the strftime convention.
         Default: "%A" - weekday as locale's full name.
        """
        days = self.weeks[0]['dates'].label(format)
        days = [d.split() for d in days]
        self.header.set_labels(days)
        self.header.queue_draw()
        self.emit('dates-changed')

    def update_days_label(self, format="%d"):
        """
        Updates the label of the days of the month to be drawn given a specific
        strftime @format.

        @param format: string, must follow the strftime convention.
         Default: "%d" - day of month as a zero-padded decimal number.
        """
        days = []
        for week in self.weeks:
            days.append(week['dates'].label(format))
        self.all_day_tasks.set_labels(days)

    def set_task_drawing_position(self, dtask, week, grid, num_week=None):
        """
        Calculates and sets the position of a @dtask inside a specific @week
        using @grid as guidance.

        @param dtask: a DrawingTask object.
        @param week: a WeekSpan object.
        @param grid: a Grid object.
        """
        task = self.req.get_task(dtask.get_id())

        start = max(task.get_start_date().date(), week.start_date)
        end = min(task.get_due_date().date(), week.end_date)
        duration = (end - start).days + 1

        x = utils.date_to_col_coord(start, week.start_date)
        w = duration
        x, y, w, h = grid.add_to_grid(x, w, id=dtask.get_label()[4])

        dtask.set_position(x, y, w, h)  # position inside this grid
        dtask.set_week_num(num_week)  # which week this task is in
        dtask.set_overflowing_L(week.start_date)
        dtask.set_overflowing_R(week.end_date)

    def get_current_year(self):
        """
        Gets the correspondent year of the days
        being displayed in the calendar view
        """
        date_middle_month = self.first_day() + datetime.timedelta(days=7)
        return date_middle_month.strftime("%B / %Y")

    def update_tasks(self):
        """ Updates and redraws everything related to the tasks """
        self.update_drawtasks()
        self.compute_size()
        self.all_day_tasks.queue_draw()

    def is_in_week_range(self, task, week):
        """
        Returns true if the given @task have either the start or due days
        between the start and end day of @week.

        @param task: a Task object
        @param week: a WeekSpan object
        """
        return (task.get_due_date().date() >= week.start_date) and \
               (task.get_start_date().date() <= week.end_date)

    def update_drawtasks(self, tasks=None):
        """
        Updates the drawtasks and calculates the position of where each one of
        them should be drawn.

        @param tasks: a Task list, containing the tasks to be drawn.
         If none is given, the tasks will be retrieved from the requester.
        """
        if not tasks:
            tasks = [self.req.get_task(t) for t in self.req.get_tasks_tree()]
        self.tasks = [t for t in tasks if self.is_in_days_range(t)]

        dtasks = []
        for i, week in enumerate(self.weeks):
            week['tasks'] = [DrawTask(t) for t in self.tasks if
                             self.is_in_week_range(t, week['dates'])]
            dtasks += week['tasks']

            week['grid'].clear_rows()
            for t in week['tasks']:
                self.set_task_drawing_position(t, week['dates'],
                                               week['grid'], i)
        self.all_day_tasks.set_tasks_to_draw(dtasks)

        # clears selected_task if it is not being showed
        if self.selected_task:
            task = self.req.get_task(self.get_selected_task)
            if task and not self.is_in_days_range(task):
                self.unselect_task()
        self.all_day_tasks.selected_task = self.selected_task

    def highlight_today_cell(self):
        """ Highlights the cell equivalent to today."""
        if self.is_today_being_shown():
            today = datetime.date.today()
            row = utils.date_to_row_coord(
                today, datetime.date(today.year, today.month, 1))
            if row == -1:
                row = self.numweeks
            col = datetime.date.today().weekday()
        else:
            row = -1
            col = -1
        self.all_day_tasks.set_highlight_cell(row, col)
        # self.header.set_highlight_cell(0, col)

    def update(self):
        """
        Updates the header, the content to be drawn (tasks), recalculates the
        size needed and then redraws everything.
        """
        self.update_drawtasks()
        self.compute_size()
        self.highlight_today_cell()
        self.update_header()
        self.update_days_label()
        self.all_day_tasks.queue_draw()

    def next(self, months=1):
        """
        Advances the dates being displayed by a given number of @months.

        @param days: integer, the number of months to advance. Default = 1.
        """
        day_in_next_month = self.last_day() + datetime.timedelta(days=1)
        self.update_weeks(day_in_next_month.year, day_in_next_month.month)
        self.update()

    def previous(self, months=1):
        """
        Regresses the dates being displayed by a given number of @months.

        @param months: integer, the number of months to go back. Default = 1.
        """
        day_in_prev_month = self.first_day() - datetime.timedelta(days=1)
        self.update_weeks(day_in_prev_month.year, day_in_prev_month.month)
        self.update()