import math
from functools import partial
from pprint import pprint
from random import randrange
import re

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.context_instructions import Color, Translate, PushMatrix, PopMatrix
from kivy.graphics.vertex_instructions import Line
from kivy.properties import NumericProperty, StringProperty, ObjectProperty, ListProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.recycleview import RecycleView
from kivy.lang import Builder
from kivy.uix.textinput import TextInput

Builder.load_file('Sidebar/sidebar.kv')


class SideBar(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.init_start, .1)

    def init_start(self, dt):
        self.graph = self.parent.children[1]


class RV(RecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []

        Clock.schedule_once(self.init_gen, .1)
        Clock.schedule_interval(self.update, .1)

    def update(self, dt):
        self.equation_gen_check()

    def equation_gen_check(self):
        """
        Generates another Equation if All are filled
        """
        if not any(data.get('equation', None) == '' for data in self.data):
            self.data.append(Equation(position=self.data[-1].get('position') + 1, ctx=self).__dict__())

    def update_position(self):
        """
        Updates Positions after Labels are Removed
        """
        for count, data in enumerate(self.data):
            data['position'] = count

    def init_gen(self, dt):
        """
        on app start, will generate EquationInput
        """
        for amount in range(0, 1):
            equation_input = Equation(position=amount, ctx=self)
            self.data.append(equation_input.__dict__())


class Equation(FloatLayout):
    r, g, b = NumericProperty(), NumericProperty(), NumericProperty()
    equation = StringProperty()
    position = NumericProperty(0)
    ctx = ObjectProperty(None)

    translate_pos = ListProperty([0, 0])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx, self.position = kwargs.get('ctx'), kwargs.get('position') or 0
        self.equation = ''

        self.line = []
        self.data = ListProperty(None)
        self.points = []
        self.latest_y_parent = None

        self.anchor_x, self.anchor_y = 0, 0

        self.r, self.g, self.b = round(randrange(1, 255) / 255, 2), round(randrange(1, 255) / 255, 2), round(
            randrange(1, 255) / 255, 2)

        self.dat = {'position': int(self.position), 'r': float(self.r), 'g': float(self.g), 'b': float(self.b),
                    'equation': str(self.equation), 'ctx': self.ctx}

        Clock.schedule_once(self.grab_parents, .1)

    def grab_parents(self, dt):
        self.graph = self.ctx.parent.graph
        self.axis_x = self.graph.axis_x
        self.axis_y = self.graph.axis_y

    def equation_check(self, equation_text: str):
        """
        updates RV data of equation input
        checks if equation is a function
        """
        for data in self.ctx.data:
            if data['position'] == self.position:
                data['equation'] = equation_text
                self.equation = equation_text
        if re.match(r'y=x', self.equation.lower()):
            # Grabs variable in equation
            variables = []
            equation = self.equation.split('=')

            for count, char in enumerate(equation):
                if char.isalpha():
                    variables.append(tuple([char, count]))
            self.symbol = variables[0]

            self.create_equation()
        else:
            self.remove_equation()

    def create_equation(self):
        """
        Creates X/Y Values
        """
        # Creates X/Y Data
        parent_data_x = []

        for marker in self.graph.axis_x.children:
            try:
                parent_data_x.append({'parent_pos': round(marker.marker_pos, 2), 'key_value': marker.key})
            except TypeError:
                pass

        parent_data_x.append(
            {'parent_pos': parent_data_x[-1]['parent_pos'] + 60, 'key_value': parent_data_x[-1]['key_value'] + 1})

        count = 0
        stop_gen = False
        for x_pos in range(0, Window.width):
            x_pos_updated = x_pos + self.graph.x
            try:
                if x_pos_updated <= parent_data_x[count].get('parent_pos'):
                    parent_key_value_x = parent_data_x[count].get('key_value')
                    x_value = round(
                        parent_key_value_x - (
                                ((parent_data_x[count].get('parent_pos')) - (x_pos + self.graph.x)) / 60),
                        2)
                    parent_pos_y, y_pos, y_value, parent_key_value_y = self.equate_y(x_value)

                    if y_pos >= self.graph.height:
                        stop_gen = True
                        continue

                    if x_pos > self.graph.width or y_pos <= 0:
                        continue

                    if not stop_gen:
                        self.data.append({'x_value': x_value, 'x_pos': x_pos_updated,
                                          'y_value': y_value, 'y_pos': y_pos,
                                          'parent_pos_x': int(parent_data_x[count].get('parent_pos')),
                                          'parent_key_value_x': parent_key_value_x,
                                          'parent_pos_y': parent_pos_y, 'parent_key_value_y': parent_key_value_y})
                else:
                    count += 1
            except (IndexError, TypeError):
                pass

        self.gen_line()

    def equate_y(self, x_value: float):
        """
        Solves for Y Value
        """
        equate = list(self.equation.split('=')[1])
        equate[self.symbol[1]] = str(x_value)
        y_value = eval(''.join(char for char in equate))
        parent_key_value_y = math.ceil(y_value)

        children = sorted(self.axis_y.children, key=int)
        parent_pos_y = None

        for marker in children:
            if marker.key == parent_key_value_y:
                parent_pos_y = marker.marker_pos
                self.latest_y_parent = marker.marker_pos

        if parent_pos_y is None:
            parent_pos_y = self.latest_y_parent + 60

        y_pos = parent_pos_y - (abs(parent_key_value_y - y_value) * 60)

        return parent_pos_y, y_pos, y_value, parent_key_value_y

    def gen_line(self):
        """
        Updates Current Lines or Generates new ones
        """
        self.points = [tuple([dat.get('x_pos'), dat.get('y_pos')]) for dat in self.data]

        for l in self.line:
            self.graph.canvas.remove(l)

        self.line = []
        self.anchor_x, self.anchor_y = 0, 0

        with self.graph.canvas:
            PushMatrix()
            x, y = self.translate_pos
            self.translate = Translate(x=x, y=y)
            line = Line(points=self.points, width=1.5, color=Color(self.r, self.g, self.b, 1))
            self.line.append(line)
        with self.graph.canvas.after:
            PopMatrix()

        self.line.append(line)

    def remove_equation(self):
        for l in self.line:
            self.graph.canvas.remove(l)

        self.line = []
        self.data = []
        self.points = []
        self.anchor_x, self.anchor_y = 0, 0
        self.latest_y_parent = None

    def __dict__(self):
        return self.dat


class EquationInput(TextInput):
    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        """
        Removes if Equation is empty and keycode is fired
        """
        super().keyboard_on_key_down(window, keycode, text, modifiers)
        if self.text == "" and len(self.parent.ctx.data) > 2:
            if keycode[1] == "backspace":
                print(self.parent.remove_equation())
        return True

    def insert_text(self, substring, from_undo=False):
        s = substring.lower()
        if not s.isspace():
            return super(EquationInput, self).insert_text(s, from_undo=from_undo)
