from django.template import loader
from django.forms import models as model_forms

from wizard import Wizard

from sample import models


class WizardFormMixin(object):
    template_name = "sample/wizard_step.html"
    form_class = None

    def get_context_data(self, **kwargs):
        context = {
            'form': self.get_form(),
        }
        context.update(kwargs)
        return context

    def get_form(self):
        form_class = self.get_form_class()
        return form_class(**self.get_form_kwargs())

    def get_form_class(self):
        return self.form_class

    def get_form_kwargs(self):
        return {
            'data': self.request.POST or None,
        }

class BaseWizardStep(object):
    template_name = None

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs

    def display(self):
        return self.get_context_data()

    def get_context_data(self, **kwargs):
        pass

    def save(self):
        pass

    def prereq(self):
        pass

    def template(self):
        return self.get_template()

    def get_template(self):
        return loader.get_template(self.template_name)

class WizardFormStep(WizardFormMixin, BaseWizardStep):
    pass

class StepOne(WizardFormStep):
    form_class = model_forms.modelform_factory(models.StepOne)

class StepTwo(WizardFormStep):
    form_class = model_forms.modelform_factory(models.StepTwo)

class StepThree(WizardFormStep):
    form_class = model_forms.modelform_factory(models.StepThree)

wizard_steps = (
    ('one', StepOne),
    ('two', StepTwo),
    ('three', StepThree),
)

def wizard_view(request, step):
    wizard = Wizard(
        'wizard',
        wizard_steps
    )
    wizard.set_step_init_args(request)
    return wizard.handle_request(request, step)