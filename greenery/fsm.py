# -*- coding: utf-8 -*-

'''
	Finite state machine library.
'''

# This is a surrogate symbol which you can use in your finite state machines
# to represent "any symbol not in the official alphabet". For example, if your
# state machine's alphabet is {"a", "b", "c", "d", fsm.anything_else}, then
# you can pass "e" in as a symbol and it will be converted to
# fsm.anything_else, then follow the appropriate transition.
anything_else = object()

def key(symbol):
	'''Ensure `fsm.anything_else` always sorts last'''
	return (symbol is anything_else, symbol)

class fsm:
	'''
		A Finite State Machine or FSM has an alphabet and a set of states. At any
		given moment, the FSM is in one state. When passed a symbol from the
		alphabet, the FSM jumps to another state (or possibly the same state).
		A map (Python dictionary) indicates where to jump.
		One state is nominated as a starting state. Zero or more states are
		nominated as final states. If, after consuming a string of symbols,
		the FSM is in a final state, then it is said to "accept" the string.
		This class also has some pretty powerful methods which allow FSMs to
		be concatenated, alternated between, multiplied, looped (Kleene star
		closure), intersected, and simplified.
		The majority of these methods are available using operator overloads.
	'''
	def __setattr__(self, name, value):
		'''Immutability prevents some potential problems.'''
		raise Exception("This object is immutable.")

	def __init__(self, alphabet, states, initial, finals, map):
		'''Initialise the hard way due to immutability.'''
		# Validation. Thanks to immutability, this only needs to be carried out once.
		if not initial in states:
			raise Exception("Initial state " + repr(initial) + " must be one of " + repr(states))
		if not finals.issubset(states):
			raise Exception("Final states " + repr(finals) + " must be a subset of " + repr(states))
		for state in map.keys():
			for symbol in map[state]:
				if not map[state][symbol] in states:
					raise Exception("Transition for state " + repr(state) + " and symbol " + repr(symbol) + " leads to " + repr(map[state][symbol]) + ", which is not a state")

		self.__dict__["alphabet"] = set(alphabet)
		self.__dict__["states"  ] = set(states)
		self.__dict__["initial" ] = initial
		self.__dict__["finals"  ] = set(finals)
		self.__dict__["map"     ] = map

	def accepts(self, input):
		'''
			This is actually mainly used for unit testing purposes.
			If `fsm.anything_else` is in your alphabet, then any symbol not in your
			alphabet will be converted to `fsm.anything_else`.
		'''
		state = self.initial
		for symbol in input:
			if anything_else in self.alphabet and not symbol in self.alphabet:
				symbol = anything_else

			# Missing transition = transition to dead state
			if not symbol in self.map[state]:
				return False

			state = self.map[state][symbol]
		return state in self.finals

	def reduce(self):
		'''
			A result by Brzozowski (1963) shows that a minimal finite state machine
			equivalent to the original can be obtained by reversing the original
			twice.
		'''
		return reversed(reversed(self))

	def __repr__(self):
		string = "fsm("
		string += "alphabet = " + repr(self.alphabet)
		string += ", states = " + repr(self.states)
		string += ", initial = " + repr(self.initial)
		string += ", finals = " + repr(self.finals)
		string += ", map = " + repr(self.map)
		string += ")"
		return string

	def __str__(self):
		rows = []

		# top row
		row = ["", "name", "final?"]
		row.extend(str(symbol) for symbol in sorted(self.alphabet, key=key))
		rows.append(row)

		# other rows
		for state in self.states:
			row = []
			if(state == self.initial):
				row.append("*")
			else:
				row.append("")
			row.append(str(state))
			if state in self.finals:
				row.append("True")
			else:
				row.append("False")
			for symbol in sorted(self.alphabet, key=key):
				if state in self.map and symbol in self.map[state]:
					row.append(str(self.map[state][symbol]))
				else:
					row.append("")
			rows.append(row)

		# column widths
		colwidths = []
		for x in range(len(rows[0])):
			colwidths.append(max(len(str(rows[y][x])) for y in range(len(rows))) + 1)

		# apply padding
		for y in range(len(rows)):
			for x in range(len(rows[y])):
				rows[y][x] = rows[y][x].ljust(colwidths[x])

		# horizontal line
		rows.insert(1, ["-" * colwidth for colwidth in colwidths])

		return "".join("".join(row) + "\n" for row in rows)

	def __add__(self, other):
		'''
			Concatenate two finite state machines together.
			For example, if self accepts "0*" and other accepts "1+(0|1)",
			will return a finite state machine accepting "0*1+(0|1)".
			Accomplished by effectively following non-deterministically.
			Call using "fsm3 = fsm1 + fsm2"
		'''
		# alphabets must be equal
		if other.alphabet != self.alphabet:
			raise Exception("Alphabets " + repr(self.alphabet) + " and " + repr(other.alphabet) + " disagree")

		# We start at the start of self. If this starting state happens to be
		# final in self, we also start at the start of other.
		if self.initial in self.finals:
			initial = frozenset([
				(0, self.initial),
				(1, other.initial),
			])
		else:
			initial = frozenset([(0, self.initial)])

		def final(state):
			for (id, substate) in state:
				# self
				if id == 0:
					if substate in self.finals:
						if other.initial in other.finals:
							return True

				# other
				elif id == 1:
					if substate in other.finals:
						return True

				else:
					raise Exception("What")

			return False

		# dedicated function accepts a "superset" and returns the next "superset"
		# obtained by following this transition in the new FSM
		def follow(current, symbol):

			next = []

			for (id, state) in current:
				if id == 0:
					next.append((0, self.map[state][symbol]))
					# final of self? merge with other initial
					if self.map[state][symbol] in self.finals:
						next.append((1, other.initial))
				elif id == 1:
					next.append((1, other.map[state][symbol]))
				else:
					raise Exception("Whaat")

			return frozenset(next)

		return crawl(self.alphabet, initial, final, follow).reduce()

	def star(self):
		'''
			If the present FSM accepts X, returns an FSM accepting X* (i.e. 0 or
			more Xes). This is NOT as simple as naively connecting the final states
			back to the initial state: see (b*ab)* for example. Instead we must create
			an articial "omega state" which is our only accepting state and which
			dives into the FSM and from which all exits return.
		'''

		# We need a new state not already used; guess first beyond current len
		omega = len(self.states)
		while omega in self.states:
			omega += 1

		initial = frozenset([omega])

		def follow(current, symbol):

			next = []

			for state in current:

				# the special new starting "omega" state behaves exactly like the
				# original starting state did
				if state == omega:
					state = self.initial

				substate = self.map[state][symbol]
				next.append(substate)

				# loop back to beginning
				if substate in self.finals:
					next.append(omega)

			return frozenset(next)

		# final if state contains omega
		def final(state):
			return omega in state

		return crawl(self.alphabet, initial, final, follow).reduce()

	def __mul__(self, multiplier):
		'''
			Given an FSM and a multiplier, return the multiplied FSM.
		'''
		if multiplier < 0:
			raise Exception("Can't multiply an FSM by " + repr(multiplier))

		if multiplier == 0:
			return epsilon(self.alphabet)

		# worked example: multiplier = 5
		output = self
		# accepts e.g. "ab"

		for i in range(multiplier - 1):
			output += self
		# now accepts e.g. "ababababab"

		return output.reduce()

	def __or__(self, other):
		'''
			Alternation.
			Return a finite state machine which accepts any sequence of symbols
			that is accepted by either self or other. Note that the set of strings
			recognised by the two FSMs undergoes a set union.
			Call using "fsm3 = fsm1 | fsm2"
		'''

		# alphabets must be equal
		if other.alphabet != self.alphabet:
			raise Exception("Alphabets " + repr(self.alphabet) + " and " + repr(other.alphabet) + " disagree")

		initial = {0 : self.initial, 1 : other.initial}

		# dedicated function accepts a "superset" and returns the next "superset"
		# obtained by following this transition in the new FSM
		def follow(current, symbol):
			next = {}
			if 0 in current and current[0] in self.map and symbol in self.map[current[0]]:
				next[0] = self.map[current[0]][symbol]
			if 1 in current and current[1] in other.map and symbol in other.map[current[1]]:
				next[1] = other.map[current[1]][symbol]
			return next

		# state is final if *any* of its internal states are final
		def final(state):
			return (0 in state and state[0] in self.finals) \
			or (1 in state and state[1] in other.finals)

		return crawl(self.alphabet, initial, final, follow).reduce()

	def __and__(self, other):
		'''
			Intersection.
			Take FSMs and AND them together. That is, return an FSM which
			accepts any sequence of symbols that is accepted by both of the original
			FSMs. Note that the set of strings recognised by the two FSMs undergoes
			a set intersection operation.
			Call using "fsm3 = fsm1 & fsm2"
		'''

		# alphabets must be equal
		if other.alphabet != self.alphabet:
			raise Exception("Alphabets " + repr(self.alphabet) + " and " + repr(other.alphabet) + " disagree")

		initial = {0 : self.initial, 1 : other.initial}

		# dedicated function accepts a "superset" and returns the next "superset"
		# obtained by following this transition in the new FSM
		def follow(current, symbol):
			next = {}
			if 0 in current and current[0] in self.map and symbol in self.map[current[0]]:
				next[0] = self.map[current[0]][symbol]
			if 1 in current and current[1] in other.map and symbol in other.map[current[1]]:
				next[1] = other.map[current[1]][symbol]
			return next

		# state is final if *all* of its substates are final
		def final(state):
			return (0 in state and state[0] in self.finals) \
			and (1 in state and state[1] in other.finals)

		return crawl(self.alphabet, initial, final, follow).reduce()

	def __xor__(self, other):
		'''
			Symmetric difference. Returns an FSM which recognises only the strings
			recognised by `self` or `other` but not both.
		'''

		# alphabets must be equal
		if other.alphabet != self.alphabet:
			raise Exception("Alphabets " + repr(self.alphabet) + " and " + repr(other.alphabet) + " disagree")

		initial = {0 : self.initial, 1 : other.initial}

		# dedicated function accepts a "superset" and returns the next "superset"
		# obtained by following this transition in the new FSM
		def follow(current, symbol):
			next = {}
			if 0 in current and current[0] in self.map and symbol in self.map[current[0]]:
				next[0] = self.map[current[0]][symbol]
			if 1 in current and current[1] in other.map and symbol in other.map[current[1]]:
				next[1] = other.map[current[1]][symbol]
			return next

		# state is final if exactly one of the substates is final
		def final(state):
			return (0 in state and state[0] in self.finals) \
			!= (1 in state and state[1] in other.finals)

		return crawl(self.alphabet, initial, final, follow).reduce()

	def everythingbut(self):
		'''
			Return a finite state machine which will accept any string NOT
			accepted by self, and will not accept any string accepted by self.
			This is more complicated if there are missing transitions, because the
			missing "dead" state must now be reified.
		'''
		alphabet = self.alphabet

		initial = {0 : self.initial}

		def follow(current, symbol):
			next = {}
			if 0 in current and current[0] in self.map and symbol in self.map[current[0]]:
				next[0] = self.map[current[0]][symbol]
			return next

		# state is final unless the original was
		def final(state):
			return not (0 in state and state[0] in self.finals)

		return crawl(alphabet, initial, final, follow).reduce()

	def __reversed__(self):
		'''
			Return a new FSM such that for every string that self accepts (e.g.
			"beer", the new FSM accepts the reversed string ("reeb").
		'''

		# Start from a composite "state-set" consisting of all final states.
		# If there are no final states, this set is empty and we'll find that
		# no other states get generated.
		initial = frozenset(self.finals)

		# Find every possible way to reach the current state-set
		# using this symbol.
		def follow(current, symbol):
			return frozenset([
				prev
				for prev in self.map
				for state in current
				if symbol in self.map[prev] and self.map[prev][symbol] == state
			])

		# A state-set is final if the initial state is in it.
		def final(state):
			return self.initial in state

		# Man, crawl() is the best!
		return crawl(self.alphabet, initial, final, follow)
		# Do not reduce() the result, since reduce() calls reversed() in turn

	def islive(self, state):
		'''A state is "live" if a final state can be reached from it.'''
		reachable = [state]
		i = 0
		while i < len(reachable):
			current = reachable[i]
			if current in self.finals:
				return True
			if current in self.map:
				for symbol in self.map[current]:
					next = self.map[current][symbol]
					if next not in reachable:
						reachable.append(next)
			i += 1
		return False

	def empty(self):
		'''
			An FSM is empty if it recognises no strings. An FSM may be arbitrarily
			complicated and have arbitrarily many final states while still recognising
			no strings because those final states may all be inaccessible from the
			initial state. Equally, an FSM may be non-empty despite having an empty
			alphabet if the initial state is final.
		'''
		return not self.islive(self.initial)

	def strings(self):
		'''
			Generate strings (lists of symbols) that this FSM accepts. Since there may
			be infinitely many of these we use a generator instead of constructing a
			static list. Strings will be sorted in order of length and then lexically.
			This procedure uses arbitrary amounts of memory but is very fast. There
			may be more efficient ways to do this, that I haven't investigated yet.
		'''

		# Many FSMs have "dead states". Once you reach a dead state, you can no
		# longer reach a final state. Since many strings may end up here, it's
		# advantageous to constrain our search to live states only.
		livestates = set(state for state in self.states if self.islive(state))

		# We store a list of tuples. Each tuple consists of an input string and the
		# state that this input string leads to. This means we don't have to run the
		# state machine from the very beginning every time we want to check a new
		# string.
		strings = []

		# Initial entry (or possibly not, in which case this is a short one)
		cstate = self.initial
		cstring = []
		if cstate in livestates:
			if cstate in self.finals:
				yield cstring
			strings.append((cstring, cstate))

		# Fixed point calculation
		i = 0
		while i < len(strings):
			(cstring, cstate) = strings[i]
			if cstate in self.map:
				for symbol in sorted(self.map[cstate], key=key):
					nstate = self.map[cstate][symbol]
					nstring = cstring + [symbol]
					if nstate in livestates:
						if nstate in self.finals:
							yield nstring
						strings.append((nstring, nstate))
			i += 1

	def equivalent(self, other):
		'''
			Two FSMs are considered equivalent if they recognise the same strings.
			Or, to put it another way, if their symmetric difference recognises no
			strings.
		'''
		return (self ^ other).empty()

def null(alphabet):
	'''
		An FSM accepting nothing (not even the empty string). This is
		demonstrates that this is possible, and is also extremely useful
		in some situations
	'''
	return fsm(
		alphabet = alphabet,
		states   = set([0]),
		initial  = 0,
		finals   = set(),
		map      = {
			0: dict([(symbol, 0) for symbol in alphabet]),
		},
	)

def epsilon(alphabet):
	'''
		Return an FSM matching an empty string, "", only.
		This is very useful in many situations
	'''
	return fsm(
		alphabet = alphabet,
		states   = set([0, 1]),
		initial  = 0,
		finals   = set([0]),
		map      = {
			0: dict([(symbol, 1) for symbol in alphabet]),
			1: dict([(symbol, 1) for symbol in alphabet]),
		},
	)

def crawl(alphabet, initial, final, follow):
	'''
		Given the above conditions and instructions, crawl a new unknown FSM,
		mapping its states, final states and transitions. Return the new FSM.
		This is a pretty powerful procedure which could potentially go on
		forever if you supply an evil version of follow().
	'''

	states = [initial]
	finals = set()
	map = {}

	# iterate over a growing list
	i = 0
	while i < len(states):
		state = states[i]

		# add to finals
		if final(state):
			finals.add(i)

		# compute map for this state
		map[i] = {}
		for symbol in sorted(alphabet, key=key):
			next = follow(state, symbol)

			try:
				j = states.index(next)
			except ValueError:
				j = len(states)
				states.append(next)

			map[i][symbol] = j

		i += 1

	return fsm(alphabet, range(len(states)), 0, finals, map)