
import inspect

from django import http
from django.core import urlresolvers
from django.template import RequestContext
from django.contrib import messages

from wizard import signals

__all__ = ('PrereqMissing', 'SaveStepException', 'Wizard')

__version__ = '0.2.3'

class PrereqMissing(Exception):
    """
    A WizardStep should raise PrereqMissing when one step must
    be completed before another but isn't.
    """

    def __init__(self, step=None, request=None, message=None):
        """
        When a step class is passed in, the wizard will redirect to
        the given step.
        """
        self.step = step
        self.prereq_message = message
        if request and message:
            messages.add_message(request, messages.ERROR, message)

class SaveStepException(Exception):
    """
    Base class for an exception during the save method.
    Indicates we can't proceed to the next step and must re-display
    the current step.
    """
    pass

class Wizard(object):
    """
    Wires together multiple WizardStep objects and takes care
    of the navigation among WizardStep objects
    """

    def __init__(self, base_url_name, steps, navigation_opts=None):
        """
        a tuple of tuples of step key names, and step objects must be
        passed into the constructor along with the base url name in the
        form of namespace:name for redirects
        """
        self.steps_callback = steps
        self.do_redirect = False
        self.steps = None
        self.steps_tuple = None
        self.base_url_name = base_url_name
        self.url_args = None
        self.url_kwargs = None
        self.args = None
        self.kwargs = None
        self.request = None
        self._current_step = None
        self.template_args = None
        self.navigation_opts = navigation_opts or {
            'wizard_save':0,
            'wizard_continue':1,
            'wizard_previous':-1,
            'wizard_next':1,
        }

    @property
    def current_step_object(self):
        """
        handle_request sets the current step, so you can't use
        this property until after a request has been handled.
        """
        return self.get_step_object_by_key(self._current_step)

    def set_common_template_args(self, args):
        """
        A dictionary of additional items the wizard should give to the
        template for each step.
        """
        self.template_args = args

    def set_step_init_args(self, *args, **kwargs):
        """
        Arguments the wizard passes to the constructor of each step.
        """
        self.args = args
        self.kwargs = kwargs

    def set_redirect_args(self, *args, **kwargs):
        """
        Arguments the wizard passes to the url reverse function to create
        the proper redirect url. Only use args or kwargs, not both.
        """
        if args and kwargs:
            raise ValueError("Don't mix *args and **kwargs, django's reverse() will not allow it!")
        self.url_args = args
        self.url_kwargs = kwargs

    def initialize_steps(self, request=None):
        if callable(self.steps_callback):
            self.steps_tuple = self.steps_callback(request)
        else:
            self.steps_tuple = self.steps_callback
        self.steps = dict(self.steps_tuple)

    def handle_request(self, request, step=None):
        """
        Main dispatch method. Figures out which step to go to for the
        current request and which one to go to next.
        """
        self.request = request
        self._current_step = step

        self.initialize_steps(request)

        if not step:
            return self.redirect(self.get_step_key_by_position(0))

        if request.method == "POST":
            return self.post(request, step)
        elif request.method == "GET":
            return self.get(request, step)

    def get_step_position(self, step):
        """
        lookup which position a given step key is in
        """
        for order, (name, _) in enumerate(self.steps_tuple):
            if name == step:
                return order
        else:
            raise ValueError(step + " not found in wizard")

    def get_step_number(self, step):
        """gets the 1 based step position"""
        return self.get_step_position(step) + 1

    def total_steps(self):
        return len(self.steps)

    def get_next_step_key(self, step):
        return self.steps_tuple[self.get_step_position(step) + 1][0]

    def get_step_key_by_position(self, position):
        if position < 0:
            return self.steps_tuple[0][0]
        elif position < self.total_steps():
            return self.steps_tuple[position][0]
        else:
            return self.steps_tuple[-1][0]

    def get_steps(self):
        """
        Allows iteration through each step name and instantiated step object

        Can be useful on a final step if you want to make do any sort of
        validation on all the steps together.
        """
        return ((name, self.get_step_object_by_key(name)) for name, _ in self.steps_tuple)

    def get_step_object_by_key(self, key):
        step = self.steps.get(key)
        if not step:
            raise http.Http404

        if inspect.isclass(step):
            self.steps[key] = self.instantiate_step(step)
            self.steps[key]._key = key
            self.steps[key]._wizard = self
            self.steps[key]._current_step = self._current_step

        return self.steps[key]

    def instantiate_step(self, step_class):
        """
        turn the class passed into the wizard into an instance of the class

        allow for different combinations of Step class constructor signatures so not
        all step classes have to have *args and **kwargs
        """
        if self.args and self.kwargs:
            step = step_class(*self.args, **self.kwargs)
        elif self.args:
            step = step_class(*self.args)
        elif self.kwargs:
            step = step_class(**self.kwargs)
        else:
            step = step_class()
        return step

    def get_url(self, step):
        if self.url_kwargs:
            self.url_kwargs['step'] = step
            return urlresolvers.reverse(self.base_url_name, kwargs=self.url_kwargs)
        elif self.url_args:
            self.url_args += (step,)
            return urlresolvers.reverse(self.base_url_name, args=self.url_args)
        else:
            return urlresolvers.reverse(self.base_url_name, kwargs={'step':step})

    def redirect(self, step):
        return http.HttpResponseRedirect(self.get_url(step))

    def post(self, request, step):
        try:
            signals.wizard_pre_save.send(self, step_key=step)
            self.get_step_object_by_key(step).save()
            signals.wizard_post_save.send(self, step_key=step)
        except SaveStepException:
            return self.render(request, self.do_display(step), step)
        else:
            return self.redirect(self.navigate(request, step))

    def handle_prereq(self, next_step, direction=None):
        """
        This calls a step's prereq method and when a PrereqMissing exception
        is raised this method will recursively find the next available step
        to go to.
        """

        try:
            self.get_step_object_by_key(next_step).prereq()
            signals.wizard_prereq.send(self, step_key=next_step)
            return next_step
        except PrereqMissing as exception:
            self.do_redirect = True

            if direction:
                pos = self.get_step_position(next_step)
                new_step_key = self.get_step_key_by_position(pos + direction)
                if new_step_key == next_step:
                    return self.handle_prereq(new_step_key, direction * -1)
                return self.handle_prereq(new_step_key, direction)
            else:
                return self.handle_prereq(exception.step)

    def navigate(self, request, step):
        """
        This determines which step we will go to next.
        """
        self.initialize_steps(request)
        next_step = step
        direction = 0
        for action, _direction in self.navigation_opts.items():
            if action in request.REQUEST:
                position = self.get_step_position(step)
                direction = _direction
                next_step = self.get_step_key_by_position(position + _direction)
                break

        return self.handle_prereq(next_step, direction)

    def get(self, request, step):
        step = self.navigate(request, step)
        if self.do_redirect:
            return self.redirect(step)
        else:
            return self.render(request, self.do_display(step), step)

    def render(self, request, data, step):
        step = self.get_step_object_by_key(step)
        template = step.template()
        mimetype = getattr(step, 'mimetype', None)
        return http.HttpResponse(template.render(RequestContext(request, data)), mimetype=mimetype)

    def do_display(self, step):
        step_object = self.get_step_object_by_key(step)
        signals.wizard_pre_display.send(self, step_key=step)
        data = step_object.display() or {}
        signals.wizard_post_display.send(self, step_key=step)
        return self.add_wizard_data_to_template(data, step)

    def add_wizard_data_to_template(self, data, step):
        """
        make some of the internals of the wizard available from the templates to allow
        dynamic building of navigation
        """
        if self.template_args:
            for key, value in self.template_args.items():
                data[key] = value
        data['step_key'] = step
        data['step'] = self.get_step_object_by_key(step)
        data['wizard'] = self
        return data

    def move_step_direction(self, direction):
        position = self.get_step_position(self._current_step)
        next_step = self.get_step_key_by_position(position + direction)
        step = self.handle_prereq(next_step, direction)
        if step != self._current_step:
            return self.get_url(step)

    def next_step_url(self):
        return self.move_step_direction(1)

    def prev_step_url(self):
        return self.move_step_direction(-1)