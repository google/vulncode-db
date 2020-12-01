# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import enum


def event(state):
    """Mark a method as an event handler, called on the given state."""

    def inner(func):
        # pylint: disable=protected-access
        if not hasattr(func, "_on_state"):
            func._on_state = set()
        func._on_state.add(state)
        return func

    return inner


def transition(from_state, to_state):
    """Mark a method as a transition handler.

    Called when a transition from current to new is about to happen.

    Args:
        from_state: Transition from
        to_state: Transition to
    Returns:
        Decorator to annotate a method. Provides a stub when used like this:
        foobar = transition(STATE1, STATE2)()
    """

    def inner(func=None):
        # pylint: disable=protected-access
        if func is None:
            # define noop
            func = lambda *args: None
            func.name = ""
        else:
            func.name = func.__qualname__
        if not hasattr(func, "_on_transition"):
            func._on_transition = set()
        func._on_transition.add((from_state, to_state))
        return func

    return inner


class NoTransition(Exception):
    """Raised if this transition was not defined."""

    def __init__(self, from_state, to_state):
        super().__init__()
        self.from_state = from_state
        self.to_state = to_state

    def __str__(self):
        return f"No transition {self.from_state} -> {self.to_state} defined"


class TransitionDenied(Exception):
    """Raised if this transition was denied by a transition handler."""

    def __init__(self, name, from_state, to_state, why):
        super().__init__()
        self.name = name
        self.from_state = from_state
        self.to_state = to_state
        self.why = why

    def __str__(self):
        return (
            f"Transition {self.from_state} -> {self.to_state} "
            + f"denied by {self.name}: {self.why}"
        )


class StateMachineMeta(enum.EnumMeta):
    """Metaclass for StateMachine."""

    def __call__(cls, *args, **kwargs):  # pylint: disable=signature-differs
        obj = object.__new__(cls)
        obj.__init__(*args, **kwargs)
        return obj

    def __new__(mcs, cls, bases, classdict):  # pylint: disable=too-many-branches
        # check if the __new__ was invoked for StateMachine itself
        try:
            is_base_cls = StateMachine not in bases
        except NameError:
            is_base_cls = True

        if not is_base_cls:
            event_listeners = collections.defaultdict(list)
            change_listeners = collections.defaultdict(list)
            remove = set()
            for name, value in classdict.items():
                if hasattr(value, "_on_state"):
                    states = value._on_state  # pylint: disable=protected-access
                    for state in states:
                        if isinstance(state, enum.Enum):
                            state = state.value
                        event_listeners[state].append(value)
                    remove.add(name)
                if hasattr(value, "_on_transition"):
                    transitions = (
                        value._on_transition
                    )  # pylint: disable=protected-access
                    for (current, next_state) in transitions:
                        if isinstance(current, enum.Enum):
                            current = current.value
                        if isinstance(next_state, enum.Enum):
                            next_state = next_state.value
                        change_listeners[(current, next_state)].append(value)
                    remove.add(name)
            for name in remove:
                del classdict[name]
            classdict["__event_listeners__"] = dict(event_listeners)
            classdict["__change_listeners__"] = dict(change_listeners)
            obj = enum.unique(super().__new__(mcs, cls, bases, classdict))
            if 0 not in obj._value2member_map_:
                raise ValueError(f"No start state found in {obj!r}")
        else:
            obj = super().__new__(mcs, cls, bases, classdict)
        return obj


class StateMachine(enum.Enum, metaclass=StateMachineMeta):
    # pylint: disable=line-too-long
    """Base class for a state machine.

    >>> class WrongValue(StateMachine):
    ...  START = 0
    ...  FOO = 0
    Traceback (most recent call last):
      [...]
    ValueError: duplicate values found in <enum 'WrongValue'>: FOO -> START
    >>> class WrongType(StateMachine):
    ...  START = 0
    ...  FOO = 'foo'
    Traceback (most recent call last):
      [...]
    TypeError: Values of WrongType must be ints
    >>> class NoStart(StateMachine):
    ...  START = 1
    ...  FOO = 2
    Traceback (most recent call last):
      [...]
    ValueError: No start state found in <enum 'NoStart'>

    >>> class FooState(StateMachine):
    ...  START = 0
    ...  FOO = 1
    ...  BAR = 2
    ...  END = 3
    ...
    ...  start_to_bar = transition(START, BAR)()
    ...
    ...  def __init__(self, reset_allowed=False):
    ...    super().__init__()
    ...    self.reset_allowed = reset_allowed
    ...
    ...  @transition(BAR, FOO)
    ...  @transition(FOO, END)
    ...  def logger(self, f, t):
    ...    print(f, '->', t)
    ...
    ...  @transition(END, START)
    ...  def verify(self, f, t):
    ...    if not self.reset_allowed:
    ...      return 'reset not allowed'
    ...
    ...  @transition(END, FOO)
    ...  def exception(self, f, t):
    ...    1/0


    >>> sm = FooState()
    >>> sm
    <FooState: FooState.START>
    >>> sm.next_state(FooState.FOO)
    Traceback (most recent call last):
    [...]
    statemachine.NoTransition: No transition FooState.START -> FooState.FOO defined
    >>> sm
    <FooState: FooState.START>
    >>> sm.next_state(FooState.BAR)
    >>> sm
    <FooState: FooState.BAR>
    >>> sm.next_state(FooState.FOO)
    FooState.BAR -> FooState.FOO
    >>> sm
    <FooState: FooState.FOO>
    >>> sm.next_state(FooState.END)
    FooState.FOO -> FooState.END
    >>> sm
    <FooState: FooState.END>
    >>> sm.next_state(FooState.START)
    Traceback (most recent call last):
    [...]
    statemachine.TransitionDenied: Transition FooState.END -> FooState.START denied by FooState.verify: reset not allowed
    >>> sm.next_state(FooState.FOO)
    Traceback (most recent call last):
    [...]
    statemachine.TransitionDenied: Transition FooState.END -> FooState.FOO denied by FooState.exception: exception occured


    >>> sm2 = FooState(reset_allowed=True)
    >>> sm2
    <FooState: FooState.START>
    >>> sm2.next_state(FooState.BAR)
    >>> sm2.next_state(FooState.FOO)
    FooState.BAR -> FooState.FOO
    >>> sm2.next_state(FooState.END)
    FooState.FOO -> FooState.END
    >>> sm2.next_state(FooState.START)
    >>> sm2
    <FooState: FooState.START>
    >>> print(FooState.dot_graph())
    digraph {
     START -> BAR [label=""];
     FOO -> END [label="FooState.logger"];
     BAR -> FOO [label="FooState.logger"];
     END -> START [label="FooState.verify"];
     END -> FOO [label="FooState.exception"];
    }
    """
    # pylint: enable=line-too-long

    @staticmethod
    def __new_member__(enumcls, value):
        if type(value) is not int:  # pylint: disable=unidiomatic-typecheck
            raise TypeError(f"Values of {enumcls.__name__} must be ints")
        obj = object.__new__(enumcls)
        obj.__init__ = lambda self: None
        return obj

    def __init__(self, state=None):
        if state is None:
            cls = type(self)
            # this calls enum.Enum.__new__ which is different from type.__new__
            state = cls.__new__(cls, 0)  # pylint: disable=no-value-for-parameter
        self._change_state(state)

    def _change_state(self, state):
        self.current_state = state
        listeners = self.__event_listeners__.get(state.value, [])
        for listener in listeners:
            listener(self)

    def next_state(self, next_state):
        """Try to transition to the given state."""

        if hasattr(self, "_value_"):
            state_machine = type(self)(self)
            return state_machine.next_state(next_state)
        try:
            transitions = self.__change_listeners__[
                (self.current_state.value, next_state.value)
            ]
            for trans in transitions:
                try:
                    res = trans(self, self.current_state, next_state)
                except Exception as ex:
                    raise TransitionDenied(
                        trans.name, self.current_state, next_state, "exception occured"
                    ) from ex
                if res is not None and res is not True:
                    raise TransitionDenied(
                        trans.name, self.current_state, next_state, res
                    )
            self._change_state(next_state)
            return self.current_state
        except KeyError:
            raise NoTransition(self.current_state, next_state) from None

    def __repr__(self):
        if hasattr(self, "_value_"):
            return f"<{self.__class__.__name__}.{self._name_}>"
        return f"<{self.__class__.__name__}: {self.current_state}>"

    def __str__(self):
        if hasattr(self, "_value_"):
            return super().__str__()
        return f"{self.__class__.__name__}: {self.current_state}"

    @classmethod
    def dot_graph(cls):
        """Returns a graphvis dot graph."""

        transitions = [
            '{} -> {} [label="{}"];'.format(
                cls._value2member_map_[f].name, cls._value2member_map_[t].name, l.name
            )
            for (f, t), ls in cls.__change_listeners__.items()
            for l in ls
        ]
        return "digraph {\n %s\n}" % "\n ".join(transitions)
