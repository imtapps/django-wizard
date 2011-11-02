from django import dispatch

wizard_pre_save = dispatch.Signal(providing_args=['step_key'])
wizard_post_save = dispatch.Signal(providing_args=['step_key'])
wizard_pre_display = dispatch.Signal(providing_args=['step_key'])
wizard_post_display = dispatch.Signal(providing_args=['step_key'])
wizard_prereq = dispatch.Signal(providing_args=['step_key'])
