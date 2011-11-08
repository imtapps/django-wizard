Django wizard uses Step classes to control page flow.

To create a wizard, you need a url route defined that is going to point to a
view and take a step parameter, like this::

        url(r'^(?P<step>[a-zA-Z]+)?$', views.my_view, name='new_wizard'),

That view then must instantiate the wizard passing it the url name, and a list of steps.
Then the wizard's handle_request method should be called and returned with the request
and the current step name (From the url)::

        def my_view(request, step):
            Wizard('new_wizard', [
            ('StepOne', mysteps.StepOne),
            ('StepTwo', mysteps.StepTwo),
        ])
        return wizard.handle_request(request, step)

The wizard also has a defaulted navigation_opts argument that can be passed in the __init__
navigation options are a dictionary with a key of a string that will map to a field in
the Request, and the value is an int. These tell the wizard what direction to go and how far
in which scenarios.

The defaults are:

        - wizard_save: 0
        - wizard_continue: 1
        - wizard_previous: -1
        - wizard_next: 1

The view can also set a few additional things on the wizard:

        * set_redirect_args(\*args, \**kwargs)
            - use this to tell the wizard what it needs to privode to django's reverse function
              when doing redirects

        * set_step_init_args(\*args, \**kwargs)
            - use this to supply additional arguments to your step class __init__'s

        * set_common_template_args(dict)
            - use this to add stuff that will always be available in all of your wizard created
              templates

The wizard will trigger the following signals:

    * wizard.signals.wizard_pre_save
    * wizard.signals.wizard_post_save
    * wizard.signals.wizard_pre_display
    * wizard.signals.wizard_post_display
    * wizard.signals.wizard_pre_prereq
    * wizard.signals.wizard_post_prereq

A Step class is just an object that must define the following methods

* display
    - only takes self as an argument and returns the object that should be
      passed to django's template engine

* save
    - only takes self as an argument and returns nothing

* template
    - only takes self as an argument and must return the template object to be used
      by the wizard to render the response
    - IE: return loader.get_template('some_template_file.html')

* prereq
    - only takes self as an argument and can raise a wizard.PrereqMissing when an error occurs in the page flow
    - the __init__ accepts an optional step key, a request and a message

    - if the step key is provided, the wizard will redirect to that step

    - if a request and message are provided it will add the message to django's messaging framework

* SaveStepException is an exception that can be raised in the save method that the wizard know that the step could not be saved and needs to be repeated

