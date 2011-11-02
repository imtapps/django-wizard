
import mock
import copy

from django import test
from django import http
from django.core import urlresolvers
from django.template import Template
from django.contrib import messages
from django.contrib.auth.models import User

import wizard

class SampleStep(object):
    def display(self):
        return {'items': range(1, 10)}

    def save(self):
        pass

    def prereq(self):
        pass

    def template(self):
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
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.calls = []

    def save(self):
        self.calls.append('save')

    def display(self):
        self.calls.append('display')

    def prereq(self):
        self.calls.append('prereq')

    def template(self):
        self.calls.append("template")
        return Template("")

class TestStepOne(MoniterStep):
    pass

class TestStepTwo(MoniterStep):
    pass

class TestStepThree(MoniterStep):
    pass

class TestStepFour(MoniterStep):
    pass

class TestStepFive(MoniterStep):
    pass

def get_class_with_missing_prereq(step, request=None, message=None):
    my_step = mock.MagicMock()
    my_step.prereq.side_effect = wizard.PrereqMissing(step, request, message)
    my_step.template.return_value = Template("")
    return my_step


class TestWizard(test.TestCase):
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

        self.wizard = wizard.Wizard('test:test1', self.steps)
        self.mock_request = mock.MagicMock()
        self.mock_request.method = 'GET'
        self.wizard.set_step_init_args(self.mock_request)

        self._wizard_pre_save = copy.copy(wizard.signals.wizard_pre_save.receivers)
        self._wizard_post_save = copy.copy(wizard.signals.wizard_post_save.receivers)
        self._wizard_pre_display = copy.copy(wizard.signals.wizard_pre_display.receivers)
        self._wizard_post_display = copy.copy(wizard.signals.wizard_post_display.receivers)

        wizard.signals.wizard_pre_save.receivers = []
        wizard.signals.wizard_post_save.receivers = []
        wizard.signals.wizard_pre_display.receivers = []
        wizard.signals.wizard_post_display.receivers = []

    def tearDown(self):
        wizard.signals.wizard_pre_save.receivers = self._wizard_pre_save
        wizard.signals.wizard_post_save.receivers = self._wizard_post_save
        wizard.signals.wizard_pre_display.receivers = self._wizard_pre_display
        wizard.signals.wizard_post_display.receivers = self._wizard_post_display	

    def test_should_instantiate_step_classes_as_needed(self):
        """
        make sure that the wizard instantiates only the classes that are requested
        """
        self.wizard.handle_request(self.mock_request, 'fourth')

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
        my_wizard = wizard.Wizard('test:test2', self.steps)
        my_wizard.set_step_init_args('asdf', 9999, abc=123, xyz=987)
        my_wizard.handle_request(self.mock_request, 'fifth')
        self.assertEqual(('asdf', 9999), my_wizard.steps['fifth'].args)
        self.assertEqual({'abc':123, 'xyz':987}, my_wizard.steps['fifth'].kwargs)

    def test_should_set_step_key_on_step_instance(self):
        step_key = 'fifth'

        my_wizard = wizard.Wizard('test:test2', self.steps)
        my_wizard.set_step_init_args('asdf', 9999, abc=123, xyz=987)
        my_wizard.handle_request(self.mock_request, step_key)

        step = my_wizard.steps[step_key]
        self.assertEqual(step_key, step._key)

    def test_should_set_wizard_instance_on_step_instance(self):
        step_key = 'fifth'

        my_wizard = wizard.Wizard('test:test2', self.steps)
        my_wizard.set_step_init_args('asdf', 9999, abc=123, xyz=987)
        my_wizard.handle_request(self.mock_request, step_key)

        step = my_wizard.steps[step_key]
        self.assertEqual(my_wizard, step._wizard)

    def test_should_set_current_step_on_instance(self):
        current_step = 'fifth'

        my_wizard = wizard.Wizard('test:test2', self.steps)
        my_wizard._current_step = current_step
        my_wizard.set_step_init_args('asdf', 9999, abc=123, xyz=987)
        my_wizard.handle_request(self.mock_request, current_step)

        self.assertEqual(current_step, my_wizard.steps[current_step]._current_step)

    @mock.patch('wizard.Wizard.get_step_object_by_key')
    def test_current_step_instance_returns_step_by_key(self, get_step):
        step_key = "One"

        my_wizard = wizard.Wizard('test:test2', self.steps)
        my_wizard._current_step = step_key

        self.assertEqual(get_step.return_value, my_wizard.current_step_object)
        get_step.assert_called_once_with(step_key)

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
        response = self.wizard.handle_request(self.mock_request)
        self.assertEqual(response['Location'], '/test/first')
        self.assertEqual(response.status_code, 302)

    @mock.patch('wizard.Wizard.navigate', mock.Mock())
    def test_should_save_current_step(self):
        """
        requesting step 0 of the wizard with a POST request should call the post method of the wizard
        as well as the post method of the first step in the wizard
        """
        self.mock_request.method = 'POST'
        self.wizard.handle_request(self.mock_request, 'first')
        self.assertTrue('save' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

    def test_should_display_current_step(self):
        """
        requesting step 0 of the wizard with a GET request should call the get method of the wizard
        as well as the get method of the first step in the wizard
        """
        self.wizard.handle_request(self.mock_request, 'first')
        self.assertTrue('display' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

    @mock.patch('wizard.Wizard.navigate', mock.Mock())
    def test_should_call_save_for_http_posts(self):
        """
        POSTing to the wizard should call the post method of the appropriate step, in this case, the first one
        """
        self.wizard.initialize_steps()
        self.mock_request.method = 'POST'
        self.wizard.post(self.mock_request, 'first')

        self.assertTrue('save' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

    def test_should_call_display_for_http_gets(self):
        """
        GETing the wizard should call the get method of the appropriate step, in this case, the first one
        """
        self.wizard.handle_request(self.mock_request, 'first')
        self.assertTrue('display' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

    def test_should_get_wizard_back(self):
        """
        passing an HttpRequest into the wizard's __call__ should return an HttpResponse with a 200 status code
        """
        response = self.wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(response.status_code, 200)

    def test_should_redirect_after_post(self):
        """
        after a post, a redirect should be returned to GET the next step
        """
        self.mock_request.method = 'POST'
        response = self.wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(response.status_code, 302)

    def test_should_not_redirect_on_post_after_error(self):
        """
        when a post encounters an error, a redirect will not be issued, instead the same step will
        be rendered again
        """
        self.mock_request.method = 'POST'
        mock_step = mock.MagicMock()
        mock_step.save.side_effect = wizard.SaveStepException("mock get error")
        self.steps[0] = ('first', mock_step)
        response = self.wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(response.status_code, 200)

    def test_should_return_same_step_after_save_error(self):
        """
        when a post encounters an error, the same step will be rendered and returned by the wizard
        and the wizard step will not advance.
        """
        self.mock_request.method = 'POST'
        mock_step = mock.MagicMock()
        mock_step.save.side_effect = wizard.SaveStepException
        self.steps[0] = ('first', mock_step)
        response = self.wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(response.status_code, 200)
        mock_step.save.assert_called_once_with()
        mock_step.display.assert_called_once_with()
        #self.assertTrue('save' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))
        #self.assertTrue('display' in self.wizard.steps['first'].calls, str(self.wizard.steps['first'].calls))

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
        response = self.wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(200, response.status_code)

    def test_should_be_able_to_pass_step_to_url(self):
        """
        this test should mimic a url like like
        http://localhost/wizard/0/
        """
        response = self.wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(200, response.status_code)

    def test_should_raise_404_when_pass_invalid_step_to_url(self):
        """
        this test should mimic a url like like
        http://localhost/wizard/999/
        """
        self.assertRaises(http.Http404, self.wizard.handle_request, self.mock_request, 'xxx')

    def test_should_remain_on_same_step_when_no_action_present(self):
        self.mock_request.location = '/'
        self.mock_request.REQUEST = {}
        self.mock_request.method = 'POST'
        response = self.wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(response['Location'], '/test/first')

    def test_should_be_able_to_get_any_step_by_request_in_any_order(self):
        """
        This test should mimic doing a GET on a url ending in each of
        the step_number's listed below where X is the step_number
        http://localhost/wizard/X/
        """
        wiz = wizard.Wizard('test:test1', self.steps)
        wiz.set_step_init_args(self.mock_request)
        for step in ['fourth', 'third', 'first', 'fifth', 'second']:
            response = wiz.handle_request(self.mock_request, step)
            self.assertEqual(200, response.status_code)

    def test_should_redirect_on_prereq_exception(self):
        """
        when a pre-req exception is raised, the wizard will redirect the client
        to that pre-req step
        """
        self.steps[3] = ('fourth', get_class_with_missing_prereq('third'))

        response = self.wizard.handle_request(self.mock_request, 'fourth')
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/third')

    def test_should_call_template_when_rendering_for_get(self):
        """
        make sure that the template method is called
        """
        self.wizard.handle_request(self.mock_request, 'first')
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
        response = self.wizard.handle_request(self.mock_request, 'fourth')
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/second')

    def test_should_be_able_to_implement_concrete_step(self):
        """
        make sure that the response for the concrete step matches what the template should render
        """
        self.steps[0] = ('first', SampleStep())
        response = self.wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(200, response.status_code)
        self.assertEqual("""
            Step: first
            <ul><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li><li>6</li><li>7</li><li>8</li><li>9</li></ul>
            """.replace(' ', ''), str(response.content).replace(' ', ''))

    @mock.patch('django.contrib.messages.add_message')
    def test_should_add_message_when_redirected_by_missing_prereqs(self, add_message):
        """
        when a missing prereq causes a step to redirect to the prereq step, a message should
        be added to the django messaging system to alert the user as to why they are not seeing
        the page they requested.  The message added to the messaging system should be the exact message
        added to the PrereqMissing exception
        """
        message_text = "This is the reason why..."
        step = mock.Mock()
        step.prereq.side_effect = wizard.PrereqMissing('first', self.mock_request, message_text)
        self.steps[3] = ('fourth', step)
        self.mock_request.user = User(id=1)#mock an 'authenticated' user object

        self.wizard.handle_request(self.mock_request, 'fourth')
        add_message.assert_called_once_with(self.mock_request, messages.ERROR, message_text)

    @mock.patch('django.contrib.messages.add_message')
    def test_should_add_multiple_messages_when_redirected_by_missing_prereqs_multiple_times(self, add_message):
        """
        when a missing prereq causes a step to redirect to the prereq step, a message should
        be added to the django messaging system to alert the user as to why they are not seeing
        the page they requested.  The message added to the messaging system should be the exact message
        added to the PrereqMissing exception
        """
        first_message = "This is the first reason why..."
        second_message = "This is the second..."
        message_text = [first_message, second_message]
        self.steps[3] = ('fourth', get_class_with_missing_prereq('third', self.mock_request, message_text[0]))
        self.steps[2] = ('third', get_class_with_missing_prereq('second', self.mock_request, message_text[1]))

        self.mock_request.user = User(id=1)#mock an 'authenticated' user object

        self.wizard.handle_request(self.mock_request, 'fourth')
        self.assertEqual([
            ((self.mock_request, messages.ERROR, first_message), {}),
            ((self.mock_request, messages.ERROR, second_message), {}),
        ], add_message.call_args_list)

    def test_should_be_able_to_access_the_wizard_object_from_a_template(self):
        """
        the wizard should add itself to the dictionary of data that is passed to the template
        this is useful for dynamically building navigation links
        """
        request = mock.Mock()
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
        response = self.wizard.handle_request(self.mock_request, 'third')
        self.assertEqual(302, response.status_code)
        self.assertEqual('/test/fifth', response['Location'])

    def test_should_allow_url_args_and_kwargs_to_be_passed_through_on_redirects(self):
        """
        if you're capturing arguments or keyword arguments in your url patterns (besides 'step' used by the wizard)
        then you should be able to pass thouse through to the wizard when it does the url lookups
        """
        self.mock_request.method = 'POST'
        my_wizard = wizard.Wizard('test:test2', self.steps)
        my_wizard.set_redirect_args(asdf=1234)
        response = my_wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(response['Location'], '/test/1234/first')

    def test_should_fail_with_invalid_kwargs_for_redirect_args(self):
        """
        make sure that the wizard doesn't make any assumptions about redirecting urls - if the url that the
        wizard is told to build, doesn't exist, it should fail
        """
        self.mock_request.method = 'POST'
        self.wizard.set_redirect_args(xxxx=9999)
        self.assertRaises(urlresolvers.NoReverseMatch, self.wizard.handle_request, self.mock_request, 'first')

    def test_should_allow_url_args_to_be_passed_positionally(self):
        """
        the wizard should also automatically add a step as the last positional argument as well as accepting the
        step as a keyword argument
        """
        self.mock_request.method = 'POST'
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        response = wiz.handle_request(self.mock_request, 'first')
        self.assertEqual(response['Location'], '/test/1234/asdf/first')

    def test_should_pass_template_args_through_wizard(self):
        """
        make sure that the wizard will pass through anything passed into set_common_template_args to the template
        """

        class DummyTestStep(TestStepOne):
            def template(self):
                """dummy method that will display the results of the template args"""
                return Template("""{% spaceless %}
                                {{ sample }} {{ other }}
                                {% endspaceless %}""")

        self.steps[0] = ('first', DummyTestStep)
        self.wizard.set_common_template_args({'sample':123, 'other':'asdf'})
        response = self.wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(200, response.status_code)
        self.assertEqual("""123asdf""".replace(' ', ''), str(response.content).replace(' ', ''))

    def test_should_stay_on_same_step_when_save_action_is_passed(self):
        """
        the wizard should allow you to "save" a step and not advance to the next step
        """
        self.mock_request.method = 'POST'
        self.mock_request.POST = {'wizard_save':'XXXXXXXXXXXXXXXXXXXX'}

        response = self.wizard.handle_request(self.mock_request)
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/first')

    def test_should_advance_step_when_continue_action_is_passed_and_invalid(self):
        """
        the wizard should allow you to "continue" to the next step
        """
        self.mock_request.method = 'POST'
        self.mock_request.REQUEST = {'wizard_continue':'VVVVDSFSDFSDF SDF SDF SDF'}

        response = self.wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/second')

    def test_should_allow_navigation_to_be_overwritten_for_advancing_form(self):
        """
        the wizard should allow you to "continue" to the next step
        """
        self.mock_request.method = 'POST'
        self.mock_request.REQUEST = {'next':'VVVVDSFSDFSDF SDF SDF SDF'}

        my_wizard = wizard.Wizard('test:test1', self.steps, {'next':1, 'remain':0})
        my_wizard.set_step_init_args(mock.Mock())

        response = my_wizard.handle_request(self.mock_request, 'first')
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/second')

    def test_allows_navigation_to_be_overwritten_for_not_advancing_form(self):
        """
        the wizard should allow you to "continue" to the next step
        """
        self.mock_request.method = 'POST'
        self.mock_request.POST = {'remain':'VVVVDSFSDFSDF SDF SDF SDF'}

        my_wizard = wizard.Wizard('test:test1', self.steps, {'next':1, 'remain':0})
        my_wizard.set_step_init_args(self.mock_request)

        response = my_wizard.handle_request(self.mock_request)
        self.assertEqual(302, response.status_code)
        self.assertEqual(response['Location'], '/test/first')

    def test_returns_one_based_step_number(self):
        self.wizard.initialize_steps()
        for step_number0, step_name in enumerate(self.steps):
            self.assertEqual(step_number0 + 1, self.wizard.get_step_number(step_name[0]))

    def test_return_total_number_of_steps(self):
        self.wizard.initialize_steps()
        self.assertEqual(len(self.steps), self.wizard.total_steps())

    def test_should_use_mime_type_from_step_when_defined(self):
        """
        the wizard will set the mimetype of the HttpResponse to the mimetype attribute
        of the current step otherwise it will use None
        """
        TestStepFive.mimetype = "application/javascript"
        response = self.wizard.handle_request(self.mock_request, 'fifth')
        self.assertEqual("application/javascript", response['Content-type'])
        delattr(TestStepFive, 'mimetype')

    def test_should_initialize_steps_in_call(self):
        self.wizard.initialize_steps = mock.Mock(wraps=self.wizard.initialize_steps)
        self.wizard.handle_request(self.mock_request)
        self.assertTrue(self.wizard.initialize_steps.called)

    def test_should_initialize_steps_in_navigate(self):
        self.wizard.initialize_steps = mock.Mock(wraps=self.wizard.initialize_steps)
        self.wizard.navigate(self.mock_request, 'second')
        self.assertTrue(self.wizard.initialize_steps.called)

    def test_should_call_steps_callback_if_callable(self):
        self.wizard.steps_callback = mock.MagicMock()
        request = mock.Mock()
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

    def test_should_reverse_direction_to_find_step_without_missing_prereq(self):
        self.steps[1] = ('second', TestStepOne)
        self.steps[2] = ('third', get_class_with_missing_prereq('first'))
        self.steps[3] = ('fourth', get_class_with_missing_prereq('fifth'))
        self.steps[4] = ('fifth', get_class_with_missing_prereq('first'))
        self.mock_request.method = 'POST'
        request = self.mock_request
        request.REQUEST = {'wizard_continue':True}
        response = self.wizard.handle_request(request, 'third')
        self.assertEqual(response['Location'], '/test/second')

    def test_should_return_first_step_if_position_is_less_than_zero(self):
        steps_tuple = ((mock.Mock(), mock.Mock()), (mock.Mock(), mock.Mock()))
        self.wizard.steps_tuple = steps_tuple
        step = self.wizard.get_step_key_by_position(-1)
        self.assertEqual(steps_tuple[0][0], step)

    def test_should_return_last_step_if_position_greater_than_length_of_steps(self):
        steps_tuple = ((mock.Mock(), mock.Mock()), (mock.Mock(), mock.Mock()))
        self.wizard.steps_tuple = steps_tuple
        self.wizard.steps = steps_tuple
        step = self.wizard.get_step_key_by_position(len(steps_tuple) + 1)
        self.assertEqual(steps_tuple[-1][0], step)

    def test_should_return_next_step_url(self):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        wiz.handle_request(self.mock_request, 'first')
        self.assertEqual(wiz.next_step_url(), '/test/1234/asdf/second')

    def test_should_return_previous_step_url(self):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        wiz.handle_request(self.mock_request, 'second')
        self.assertEqual(wiz.prev_step_url(), '/test/1234/asdf/first')

    def test_should_skip_steps_with_missing_prereqs_when_moving_forward(self):
        self.steps[1] = ('second', get_class_with_missing_prereq('first'))
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        wiz.handle_request(self.mock_request, 'first')
        self.assertEqual(wiz.next_step_url(), '/test/1234/asdf/third')

    def test_should_return_none_when_previous_step_has_not_changed(self):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        wiz.handle_request(self.mock_request, 'first')
        self.assertEqual(wiz.prev_step_url(), None)

    def test_should_return_none_when_next_step_has_not_changed(self):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        wiz.handle_request(self.mock_request, 'fifth')
        self.assertEqual(wiz.next_step_url(), None)

    @mock.patch('wizard.signals.wizard_pre_save.send')
    def test_sends_pre_save_signal_in_post(self, send_presave):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        self.mock_request.method = 'POST'
        self.mock_request.POST = {}
        wiz.handle_request(self.mock_request, 'first')
        send_presave.assert_called_once_with(wiz, step_key='first')

    @mock.patch('wizard.signals.wizard_post_save.send')
    def test_sends_post_save_signal_in_post(self, send_postsave):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        self.mock_request.method = 'POST'
        self.mock_request.POST = {}
        wiz.handle_request(self.mock_request, 'first')
        send_postsave.assert_called_once_with(wiz, step_key='first')

    @mock.patch.object(TestStepOne, 'save', mock.Mock(side_effect=wizard.SaveStepException))
    @mock.patch('wizard.signals.wizard_post_save.send')
    def test_does_not_send_post_save_signal_in_post_on_save_step_exception(self, send_postsave):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.set_redirect_args(1234, 'asdf')
        self.mock_request.method = 'POST'
        self.mock_request.POST = {}
        wiz.handle_request(self.mock_request, 'first')
        self.assertFalse(send_postsave.called)

    @mock.patch('wizard.signals.wizard_pre_display.send')
    def test_sends_pre_display_signal_in_do_display(self, send_predisplay):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.handle_request(self.mock_request, 'first')
        send_predisplay.assert_called_once_with(wiz, step_key='first')

    @mock.patch('wizard.signals.wizard_post_display.send')
    def test_sends_post_display_signal_in_do_display(self, send_postdisplay):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.handle_request(self.mock_request, 'first')
        send_postdisplay.assert_called_once_with(wiz, step_key='first')

    @mock.patch('wizard.signals.wizard_prereq.send')
    def test_sends_prereq_signal_in_handle_prereq(self, send_prereq):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.steps = dict(self.steps)
        wiz.handle_prereq('fourth')
        send_prereq.assert_called_once_with(wiz, step_key='fourth')

    @mock.patch('wizard.signals.wizard_prereq.send')
    def test_prereq_exceptions_are_caught_when_raised_by_prereq_signal(self, send_prereq):
        send_prereq.side_effect = lambda *args, **kwargs:(e for e in [wizard.PrereqMissing])
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.steps = dict(self.steps)
        try:
            wiz.handle_prereq('fourth')
        except wizard.PrereqMissing:
            self.fail("Prereq should not have been raised")

    def test_request_is_none_before_handle_request(self):
        wiz = wizard.Wizard('test:test3', self.steps)
        self.assertEqual(None, wiz.request)

    def test_request_is_set_after_handle_request(self):
        wiz = wizard.Wizard('test:test3', self.steps)
        request = mock.Mock()
        wiz.handle_request(request, 'first')
        self.assertEqual(request, wiz.request)

    def test_get_steps_returns_step_key_and_instantiated_steps(self):
        wiz = wizard.Wizard('test:test3', self.steps)
        wiz.initialize_steps()

        zipped_steps = zip(self.steps, wiz.get_steps())
        for declared_steps, instantiated_steps in zipped_steps:
            self.assertEqual(declared_steps[0], instantiated_steps[0])
            self.assertIsInstance(instantiated_steps[1], declared_steps[1])


