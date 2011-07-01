"Tests for the form wizard"
from mock import Mock, MagicMock, patch

from django import test
from django import http
from django.core import urlresolvers
from django.template import Template
from django.contrib import messages
from django.contrib.auth.models import User
from wizard import forms

class MoniterProxy(object):
    "this proxy will allow the tests to see what methods are called"
    def __init__(self, instance):
        "proxy some object instance"
        self.instance = instance
        self.calls = []

    def __getattribute__(self, attr):
        """
        fake the proxy so it looks like an instance of the same type as the object it wraps
        """
        if attr == '__class__':
            return self.instance.__class__
        else:
            return object.__getattribute__(self, attr)

    def __getattr__(self, attr):
        "wrap attribute access and build a list of which attributes are accessed"
        self.calls.append(attr)
        return getattr(self.instance, attr)

class MockRequest(object):
    "this is a fake HttpRequest object to use in testing"
    POST = {}
    REQUEST = {}
    def __init__(self, method):
        "the method of the HttpRequest must be passed into the constructor"
        self.method = method
        self.path = '/'

class MockPostErrorWizardStep(forms.WizardStep):
    """
    this class is a fake wizard step that will raise an error when posted to
    """
    def save(self):
        "fake a post call and raise an error"
        raise forms.SaveStepException("mock get error")

class SampleStep(object):
    "sample WizardStemp implementation"
    def display(self):
        "sample get method"
        return {'items': range(1, 10)}

    def save(self):
        "sample post method"
        pass

    def prereq(self):
        "sample prereq method"
        pass

    def template(self):
        "return the template to be used"

        return Template("""
        {% spaceless %}
        Step: {{step_key}}
        <ul>
        {% for item in items %}
            <li>{{item}}</li>
        {% endfor %}
        </ul>
        {% endspaceless %}
        """)

class MoniterStep(object):
    "this is a dummy step that will moniter what methods are called"
    def __init__(self, *args, **kwargs):
        "hold onto the args and create a calls that will be used to track what is done"
        self.args = args
        self.kwargs = kwargs
        self.calls = []

    def save(self):
        "record that save was called"
        self.calls.append('save')

    def display(self):
        "record that display was called"
        self.calls.append('display')

    def prereq(self):
        "record that prereq was called"
        self.calls.append('prereq')

    def template(self):
        "record that template was called and return an empty template"
        self.calls.append("template")
        return Template("")

class TestStepOne(MoniterStep):
    "dummy step"
    pass
class TestStepTwo(MoniterStep):
    "dummy step"
    pass
class TestStepThree(MoniterStep):
    "dummy step"
    pass
class TestStepFour(MoniterStep):
    "dummy step"
    pass
class TestStepFive(MoniterStep):
    "dummy step"
    pass

def get_class_with_missing_prereq(step, request=None, message=None):
    "return a class that can be used that has a prereq to the passed in step"
    class PrereqClass(MoniterStep):
        "dummy step class"
        def prereq(self):
            "prereq method that will record that prereq is called and raise an exception"

            self.calls.append('prereq')
            raise forms.PrereqMissing(step, request, message)
    return PrereqClass

class TestWizard(test.TestCase):
    """
    these tests will test the functionaility of the form wizard
    """

    urls = 'wizard.test_urls'

    def setUp(self):
        """
        build some 'fake' wizard steps (wrapped by a proxy in order to moniter what they're doing)
        as well as a 'fake' wizard also proxied
        """
        self.steps = [
                ('first', TestStepOne),
                ('second', TestStepTwo),
                ('third', TestStepThree),
                ('fourth', TestStepFour),
                ('fifth', TestStepFive),
        ]

        self.wizard = forms.Wizard('test:test1', self.steps)
        self.wizard.set_step_init_args(MockRequest("GET"))

    def test_should_instantiate_step_classes_as_needed(self):
        """
        make sure that the wizard instantiates only the classes that are requested
        """
        self.wizard.handle_request(MockRequest("GET"), 'fourth')

        self.assertEqual('type', type(self.wizard.steps['first']).__name__, self.wizard.steps['fourth'])
        self.assertEqual('type', type(self.wizard.steps['second']).__name__, self.wizard.steps['fourth'])
        self.assertEqual('type', type(self.wizard.steps['third']).__name__, self.wizard.steps['fourth'])
        self.assertNotEqual('type', type(self.wizard.steps['fourth']).__name__, self.wizard.steps['fourth'])
        self.assertEqual('type', type(self.wizard.steps['fifth']).__name__, self.wizard.steps['fourth'])

    def test_should_pass_args_and_kwargs_on_to_steps(self):
        """
        make sure that when the wizard intantiates a step that it passes the corrects args and kwargs to
        the constructor
        """
        wizard = forms.Wizard('test:test2', self.steps)
        wizard.set_step_init_args('asdf', 9999, abc=123, xyz=987)
        wizard.handle_request(MockRequest("GET"), 'fifth')
        self.assertEqual(('asdf', 9999), wizard.steps['fifth'].args)
        self.assertEqual({'abc':123, 'xyz':987}, wizard.steps['fifth'].kwargs)

    def test_should_set_step_key_on_step_instance(self):
        step_key = 'fifth'

        wizard = forms.Wizard('test:test2', self.steps)
        wizard.set_step_init_args('asdf', 9999, abc=123, xyz=987)
        wizard.handle_request(MockRequest("GET"), step_key)

        step = wizard.steps[step_key]
        self.assertEqual(step_key, step._key)

    def test_should_set_wizard_instance_on_step_instance(self):
        step_key = 'fifth'

        wizard = forms.Wizard('test:test2', self.steps)
        wizard.set_step_init_args('asdf', 9999, abc=123, xyz=987)
        wizard.handle_request(MockRequest("GET"), step_key)

        step = wizard.steps[step_key]
        self.assertEqual(wizard, step._wizard)

    def test_should_set_current_step_on_instance(self):
        current_step = 'fifth'

        wizard = forms.Wizard('test:test2', self.steps)
        wizard._current_step = current_step
        wizard.set_step_init_args('asdf', 9999, abc=123, xyz=987)
        wizard.handle_request(MockRequest("GET"), current_step)

        self.assertEqual(current_step, wizard.steps[current_step]._current_step)

    def test_should_be_able_to_get_test_url(self):
        """
        make sure that the tests can see the test urls
        """
        client = test.Client()
        response = client.get('/test/step/')
        self.assertEqual(200, response.status_code)

    def test_should_redirect_default_first_step(self):
        """
        the root url of the wizard should be able to determine what the first step is
        """
        response = self.wizard.handle_request(MockRequest("GET"))
        self.assertEqual(response['Location'], '/test/first')
        self.assertEqual(response.status_code, 302)

    @patch('wizard.forms.Wizard.navigate', Mock())
    def test_should_save_current_step(self):
        """
        requesting step 0 of the wizard with a POST request should call the post method of the wizard
        as well as the post method of the first step in the wizard
        """
        self.wizard.handle_request(MockRequest('POST'), 'first')
        self.assertTrue('save' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

    def test_should_display_current_step(self):
        """
        requesting step 0 of the wizard with a GET request should call the get method of the wizard
        as well as the get method of the first step in the wizard
        """
        self.wizard.handle_request(MockRequest('GET'), 'first')
        self.assertTrue('display' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

    @patch('wizard.forms.Wizard.navigate', Mock())
    def test_should_call_save_for_http_posts(self):
        """
        POSTing to the wizard should call the post method of the appropriate step, in this case, the first one
        """
        self.wizard.initialize_steps()
        self.wizard.post(MockRequest("POST"), 'first')

        self.assertTrue('save' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

    def test_should_call_display_for_http_gets(self):
        """
        GETing the wizard should call the get method of the appropriate step, in this case, the first one
        """
        self.wizard.handle_request(MockRequest("GET"), 'first')
        self.assertTrue('display' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

    def test_should_get_wizard_back(self):
        """
        passing an HttpRequest into the wizard's __call__ should return an HttpResponse with a 200 status code
        """
        request = MockRequest("GET")
        response = self.wizard.handle_request(request, 'first')
        self.assertEqual(response.status_code, 200)

    def test_should_redirect_after_post(self):
        """
        after a post, a redirect should be returned to GET the next step
        """
        request = MockRequest("POST")
        response = self.wizard.handle_request(request, 'first')
        self.assertEqual(response.status_code, 302)

    def test_should_not_redirect_on_post_after_error(self):
        """
        when a post encounters an error, a redirect will not be issued, instead the same step will
        be rendered again
        """
        request = MockRequest("POST")
        self.steps[0] = ('first', MockPostErrorWizardStep())
        response = self.wizard.handle_request(request, 'first')
        self.assertEqual(response.status_code, 200)

    def test_should_return_same_step_after_save_error(self):
        """
        when a post encounters an error, the same step will be rendered and returned by the wizard
        and the wizard step will not advance.
        """
        request = MockRequest("POST")
        self.steps[0] = ('first', MoniterProxy(MockPostErrorWizardStep()))
        response = self.wizard.handle_request(request, 'first')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('save' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))
        self.assertTrue('display' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

    def test_should_include_current_step_in_response(self):
        """
        the wizard will store the "state" (meaning the current step) in the dictionary passed
        into the template for each step
        """
        self.wizard.initialize_steps()
        data = self.wizard.add_wizard_data_to_template({}, 'first')
        self.assertTrue('step' in data, str(data))

    def test_should_be_able_to_get_root_url(self):
        """
        this test should mimic a url like like
        http://localhost/wizard/
        """
        response = self.wizard.handle_request(MockRequest('GET'), 'first')
        self.assertEqual(200, response.status_code)

    def test_should_be_able_to_pass_step_to_url(self):
        """
        this test should mimic a url like like
        http://localhost/wizard/0/
        """
        response = self.wizard.handle_request(MockRequest('GET'), 'first')
        self.assertEqual(200, response.status_code)

    def test_should_raise_404_when_pass_invalid_step_to_url(self):
        """
        this test should mimic a url like like
        http://localhost/wizard/999/
        """
        self.assertRaises(http.Http404, self.wizard.handle_request, MockRequest('GET'), 'xxx')

    def test_should_remain_on_same_step_when_no_action_present(self):
        response = self.wizard.handle_request(MockRequest('POST'), 'first')
        self.assertEqual(response['Location'], '/test/first')

    def test_should_be_able_to_get_any_step_by_request_in_any_order(self):
        """
        This test should mimic doing a GET on a url ending in each of
        the step_number's listed below where X is the step_number
        http://localhost/wizard/X/
        """
        request = MockRequest("GET")
        wiz = forms.Wizard('test:test1', self.steps)
        wiz.set_step_init_args(request)
        for step in ['fourth', 'third', 'first', 'fifth', 'second']:
            response = wiz.handle_request(request, step)
            self.assertEqual(200, response.status_code)

    def test_should_redirect_on_prereq_exception(self):
        """
        when a pre-req exception is raised, the wizard will redirect the client
        to that pre-req step
        """
        self.steps[3] = ('fourth', get_class_with_missing_prereq('third'))

        response = self.wizard.handle_request(MockRequest('GET'), 'fourth')
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/third')

    def test_should_call_template_when_rendering_for_get(self):
        """
        make sure that the template method is called
        """
        self.wizard.handle_request(MockRequest("GET"), 'first')
        self.assertTrue('template' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

    def test_should_handle_nested_prereq_without_multiple_redirects(self):
        """
        if you do a GET for step 3 of the wizard and step 3 has a missing pre-req for step 2,
        and step 2 has a missing pre-req for step 1, then a redirect to step 1 should be returned
        --- there should only be a single redirect - not one for step 2 and a second for step 1
        --- the wizard will determine the first step available with all satisfied pre-reqs
        --- (starting at the requested page) and issue a single redirect
        """

        self.steps[3] = ('fourth', get_class_with_missing_prereq('third'))
        self.steps[2] = ('third', get_class_with_missing_prereq('second'))
        response = self.wizard.handle_request(MockRequest('GET'), 'fourth')
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/second')

    def test_should_be_able_to_implement_concrete_step(self):
        """
        make sure that the response for the concrete step matches what the template should render
        """
        self.steps[0] = ('first', SampleStep())
        response = self.wizard.handle_request(MockRequest("GET"), 'first')
        self.assertEqual(200, response.status_code)
        self.assertEqual("""
            Step: first
            <ul><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li><li>6</li><li>7</li><li>8</li><li>9</li></ul>
            """.replace(' ', ''), str(response.content).replace(' ', ''))

    def test_should_add_message_when_redirected_by_missing_prereqs(self):
        """
        when a missing prereq causes a step to redirect to the prereq step, a message should
        be added to the django messaging system to alert the user as to why they are not seeing
        the page they requested.  The message added to the messaging system should be the exact message
        added to the PrereqMissing exception
        """
        request = MockRequest("GET")
        message_text = "This is the reason why..."

        self.steps[3] = ('fourth', get_class_with_missing_prereq('first', request, message_text))

        request.user = User(id=1)#mock an 'authenticated' user object

        self.wizard.handle_request(request, 'fourth')
        message_list = list(messages.get_messages(request))
        self.assertEqual([message_text], message_list)

    def test_should_add_multiple_messages_when_redirected_by_missing_prereqs_multiple_times(self):
        """
        when a missing prereq causes a step to redirect to the prereq step, a message should
        be added to the django messaging system to alert the user as to why they are not seeing
        the page they requested.  The message added to the messaging system should be the exact message
        added to the PrereqMissing exception
        """
        request = MockRequest("GET")
        message_text = ["This is the first reason why...", "This is the second..."]
        self.steps[3] = ('fourth', get_class_with_missing_prereq('third', request, message_text[0]))
        self.steps[2] = ('third', get_class_with_missing_prereq('second', request, message_text[1]))

        request.user = User(id=1)#mock an 'authenticated' user object

        self.wizard.handle_request(request, 'fourth')
        message_list = list(messages.get_messages(request))
        self.assertEqual(message_text, message_list, str(message_list) + " is not " + str(message_text))

    def test_should_be_able_to_access_the_wizard_object_from_a_template(self):
        """
        the wizard should add itself to the dictionary of data that is passed to the template
        this is useful for dynamically building navigation links
        """
        request = Mock()
        request.method = 'GET'
        self.wizard.initialize_steps()
        data = self.wizard.do_display('first')
        self.assertTrue('wizard' in data, str(data))

    def test_should_be_able_to_skip_ahead_to_future_form(self):
        """
        in the scenario where you have a form that has a prerequisite, but the prerequsite is optional, (therefore
        so is the step with the prerequisite to the optional step) the wizard should allow you to skip forward
        by raising a PrereqMissing exception and passing a future step name into it
        """
        self.steps[2] = ('third', get_class_with_missing_prereq('fifth'))
        response = self.wizard.handle_request(MockRequest("GET"), 'third')
        self.assertEqual(302, response.status_code)
        self.assertEqual('/test/fifth', response['Location'])

    def test_should_allow_url_args_and_kwargs_to_be_passed_through_on_redirects(self):
        """
        if you're capturing arguments or keyword arguments in your url patterns (besides 'step' used by the wizard)
        then you should be able to pass thouse through to the wizard when it does the url lookups
        """
        wizard = forms.Wizard('test:test2', self.steps)
        wizard.set_redirect_args(asdf=1234)
        response = wizard.handle_request(MockRequest('POST'), 'first')
        self.assertEqual(response['Location'], '/test/1234/first')

    def test_should_fail_with_invalid_kwargs_for_redirect_args(self):
        """
        make sure that the wizard doesn't make any assumptions about redirecting urls - if the url that the
        wizard is told to build, doesn't exist, it should fail
        """
        self.wizard.set_redirect_args(xxxx=9999)
        self.assertRaises(urlresolvers.NoReverseMatch, self.wizard.handle_request, MockRequest('POST'), 'first')

    def test_should_allow_url_args_to_be_passed_positionally(self):
        """
        the wizard should also automatically add a step as the last positional argument as well as accepting the
        step as a keyword argument
        """
        wiz = forms.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        response = wiz.handle_request(MockRequest("POST"), 'first')
        self.assertEqual(response['Location'], '/test/1234/asdf/first')

    def test_should_pass_template_args_through_wizard(self):
        """
        make sure that the wizard will pass through anything passed into set_common_template_args to the template
        """

        class DummyTestStep(TestStepOne):
            def template(self):
                "dummy method that will display the results of the template args"
                return Template("""{% spaceless %}
                                {{ sample }} {{ other }}
                                {% endspaceless %}""")

        self.steps[0] = ('first', DummyTestStep)
        self.wizard.set_common_template_args({'sample':123, 'other':'asdf'})
        response = self.wizard.handle_request(MockRequest("GET"), 'first')
        self.assertEqual(200, response.status_code)
        self.assertEqual("""123asdf""".replace(' ', ''), str(response.content).replace(' ', ''))

    def test_should_stay_on_same_step_when_save_action_is_passed(self):
        """
        the wizard should allow you to "save" a step and not advance to the next step
        """

        request = MockRequest('POST')
        request.POST = {'wizard_save':'XXXXXXXXXXXXXXXXXXXX'}

        response = self.wizard.handle_request(request)
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/first')

    def test_should_advance_step_when_continue_action_is_passed_and_invalid(self):
        """
        the wizard should allow you to "continue" to the next step
        """
        request = MockRequest('POST')
        request.REQUEST = {'wizard_continue':'VVVVDSFSDFSDF SDF SDF SDF'}

        response = self.wizard.handle_request(request, 'first')
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/second')

    def test_should_allow_navigation_to_be_overwritten_for_advancing_form(self):
        """
        the wizard should allow you to "continue" to the next step
        """
        request = MockRequest('POST')
        request.REQUEST = {'next':'VVVVDSFSDFSDF SDF SDF SDF'}

        wizard = forms.Wizard('test:test1', self.steps, {'next':1, 'remain':0})
        wizard.set_step_init_args(MockRequest("GET"))

        response = wizard.handle_request(request, 'first')
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/second')

    def test_should_allow_navigation_to_be_overwritten_for_not_advancing_form(self):
        """
        the wizard should allow you to "continue" to the next step
        """
        request = MockRequest('POST')
        request.POST = {'remain':'VVVVDSFSDFSDF SDF SDF SDF'}

        wizard = forms.Wizard('test:test1', self.steps, {'next':1, 'remain':0})
        wizard.set_step_init_args(request)

        response = wizard.handle_request(request)
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/first')

    def test_should_return_step_number(self):
        "should return the 1 based position for each step name"
        self.wizard.initialize_steps()
        for step_number0, step_name in enumerate(self.steps):
            self.assertEqual(step_number0 + 1, self.wizard.get_step_number(step_name[0]))

    def test_should_return_total_steps(self):
        "returns total number of steps"
        self.wizard.initialize_steps()
        self.assertEqual(len(self.steps), self.wizard.total_steps())

    def test_should_use_mime_type_from_step_when_defined(self):
        """
        the wizard will set the mimetype of the HttpResponse to the mimetype attribute
        of the current step otherwise it will use None
        """
        TestStepFive.mimetype = "application/javascript"
        response = self.wizard.handle_request(MockRequest("GET"), 'fifth')
        self.assertEqual("application/javascript", response['Content-type'])
        delattr(TestStepFive, 'mimetype')

    def test_should_initialize_steps_in_call(self):
        self.wizard.initialize_steps = Mock(wraps=self.wizard.initialize_steps)
        self.wizard.handle_request(MockRequest("GET"))
        self.assertTrue(self.wizard.initialize_steps.called)

    def test_should_initialize_steps_in_navigate(self):
        self.wizard.initialize_steps = Mock(wraps=self.wizard.initialize_steps)
        self.wizard.navigate(MockRequest("GET"), 'second')
        self.assertTrue(self.wizard.initialize_steps.called)

    def test_should_call_steps_callback_if_callable(self):
        self.wizard.steps_callback = MagicMock()
        request = Mock()
        self.wizard.initialize_steps(request)
        self.wizard.steps_callback.assert_called_once_with(request)

    def test_should_set_steps_tuple_as_steps_callback_if_not_callable(self):
        steps_callback = self.steps
        self.wizard.steps_callback = steps_callback
        self.wizard.initialize_steps()
        self.assertEqual(steps_callback, self.wizard.steps_tuple)

    def test_should_set_steps_as_dict_of_steps_tuple(self):
        self.wizard.steps_callback = self.steps
        self.wizard.initialize_steps()
        self.assertEqual(dict(self.steps), self.wizard.steps)

    def test_should_not_infinately_recurse_but_stop_on_last_step(self):
        self.steps[1] = ('second', get_class_with_missing_prereq('first'))
        self.steps[2] = ('third', get_class_with_missing_prereq('first'))
        self.steps[3] = ('fourth', get_class_with_missing_prereq('fifth'))
        self.steps[4] = ('fifth', get_class_with_missing_prereq('first'))
        request = MockRequest("POST")
        request.REQUEST = {'wizard_continue':True}
        response = self.wizard.handle_request(request, 'first')
        self.assertEqual(response['Location'], '/test/fifth')

    def test_should_return_first_step_if_position_is_less_than_zero(self):
        steps_tuple = ((Mock(), Mock()), (Mock(), Mock()))
        self.wizard.steps_tuple = steps_tuple
        step = self.wizard.get_step_key_by_position(-1)
        self.assertEqual(steps_tuple[0][0], step)

    def test_should_return_last_step_if_position_greater_than_length_of_steps(self):
        steps_tuple = ((Mock(), Mock()), (Mock(), Mock()))
        self.wizard.steps_tuple = steps_tuple
        self.wizard.steps = steps_tuple
        step = self.wizard.get_step_key_by_position(len(steps_tuple) + 1)
        self.assertEqual(steps_tuple[-1][0], step)

    def test_should_return_next_step_url(self):
        wiz = forms.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        wiz.handle_request(MockRequest("GET"), 'first')
        self.assertEqual(wiz.next_step_url(), '/test/1234/asdf/second')

    def test_should_return_previous_step_url(self):
        wiz = forms.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        wiz.handle_request(MockRequest("GET"), 'second')
        self.assertEqual(wiz.prev_step_url(), '/test/1234/asdf/first')

    def test_should_skip_steps_with_missing_prereqs_when_moving_forward(self):
        self.steps[1] = ('second', get_class_with_missing_prereq('first'))
        wiz = forms.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        wiz.handle_request(MockRequest("GET"), 'first')
        self.assertEqual(wiz.next_step_url(), '/test/1234/asdf/third')

    def test_should_return_none_when_previous_step_has_not_changed(self):
        wiz = forms.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        wiz.handle_request(MockRequest("GET"), 'first')
        self.assertEqual(wiz.prev_step_url(), None)

    def test_should_return_none_when_next_step_has_not_changed(self):
        wiz = forms.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        wiz.handle_request(MockRequest("GET"), 'fifth')
        self.assertEqual(wiz.next_step_url(), None)