import itertools
import sys

# Template script for § 2.6 in Brattico, P. (2024). Computational generative grammar.

lexicon = {'a': {'a'}, 'b': {'b'}, 'c': {'c'}, 'd': {'d'},
           'the': {'D'},
           'dog': {'N'},
           'bark': {'V', 'V/INTR'},
           'ing': {'N', '!wCOMP:V', 'ε'},
           'man': {'N'},
           'bite': {'V', 'V/TR'},
           'v': {'v', 'V'},
           'en': {'v*', 'V', 'EPP', '!wCOMP:V'},
           'was': {'T', '+COMP:v*'},
           'seem': {'V', 'EPP', '+COMP:Inf'},
           'to': {'Inf', '+SPEC:D,Ø', 'EPP'},
           'leave': {'V', 'V/INTR'},
           'does': {'T', 'Aux'},
           'ed': {'T', '!wCOMP:V'},
           'which': {'D', 'wh'},
           'T': {'T', '!wCOMP:V'},
           'frequently': {'Adv', 'adjoin:V'},
           'C(wh)': {'C', 'wh', '!wCOMP:Aux', '+SPEC:wh'}
           }

lexical_redundancy_rules = {'D': {'+COMP:N', '+SPEC:Ø'},
                            'V/TR': {'+COMP:D', '+SPEC:X'},
                            'V/INTR': {'+SPEC:Ø,X', '+COMP:D'},
                            'T': {'+COMP:V', 'EPP'},
                            'v': {'+COMP:V', '+SPEC:D', '!wCOMP:V'},
                            'v*': {'+COMP:V'},
                            'C': {'+COMP:T'},
                            'Adv': {'+SPEC:X', '+COMP:X'},
                            'Inf': {'+COMP:V', '+SPEC:D'},
                            'N': {'+COMP:Ø', '+SPEC:Ø'}}

def fformat(f):
    if f.startswith('+COMP') or f.startswith('+SPEC'):
        return f.split(':')[0], set(f.split(':')[1].split(','))
    return None, None

class Lexicon:
    """Stores lexical knowledge"""
    def __init__(self):
        self.lexical_entries = dict()
        self.compose_lexicon()

    def compose_lexicon(self):
        """Composes the lexicon from the list of words and (later) lexical redundancy rules"""
        for lex in lexicon.keys():
            self.lexical_entries[lex] = lexicon[lex]
            for trigger_feature in lexical_redundancy_rules:
                if trigger_feature in self.lexical_entries[lex]:
                    self.lexical_entries[lex] = self.lexical_entries[lex] | lexical_redundancy_rules[trigger_feature]

    def retrieve(self, name):
        """Retrieves lexical items from the speaker lexicon and wraps them
        into zero-level phrase structure objects"""
        X0 = PhraseStructure()
        X0.features = self.lexical_entries[name]
        X0.zero = True
        X0.phonological_exponent = name
        return X0

class PhraseStructure:
    """Simple asymmetric binary-branching bare phrase structure formalism"""
    log_report = ''
    chain_index = 0
    def __init__(self, X=None, Y=None):
        self.const = (X, Y)
        self.features = set()
        self.mother_ = None
        if X:
            X.mother_ = self
        if Y:
            Y.mother_ = self
        self.zero = False
        self.phonological_exponent = ''
        self.elliptic = False
        self.chain_index = 0

    def copy(X):
        """Copies whole constituent (recursively)"""
        if not X.terminal():
            Y = PhraseStructure(X.left().copy(), X.right().copy())
        else:
            Y = PhraseStructure()
        Y.copy_properties(X)
        return Y

    def copy_properties(Y, X):
        """Copies the properties of a constituent"""
        Y.phonological_exponent = X.phonological_exponent
        Y.features = X.features.copy()
        Y.elliptic = X.elliptic
        Y.chain_index = X.chain_index
        Y.zero = X.zero

    def chaincopy(X):
        """Copies a constituent and adds anything assumed in the grammatical theory,
        in this case makes the source elliptic and provides a chain subscript index"""
        X.label_chain()
        Y = X.copy()
        X.elliptic = True
        return Y

    def label_chain(X):
        """Generates subscripts for phrasal chains"""
        if not X.zero_level() and X.chain_index == 0:
            PhraseStructure.chain_index += 1
            X.chain_index = PhraseStructure.chain_index

    def mother(X):
        """Abstraction for mother node"""
        return X.mother_

    def set_mother(X, Y):
        """Abstraction for providing a mother node"""
        X.mother_ = Y

    def left(X):
        """Definition (abstraction) for the notion of left daughter"""
        return X.const[0]

    def right(X):
        """Definition(abstraction) for the notion of right daughter"""
        return X.const[1]

    def isLeft(X):
        return X.mother() and X.mother().left() == X

    def isRight(X):
        return X.mother() and X.mother().right() == X

    def sister(X):
        """Definition for sisterhood"""
        return next((x for x in X.mother().const if x != X), None)

    def complement(X):
        """Complement is right sister of a zero-level objects"""
        if X.zero_level() and X.isLeft():
            return X.sister()

    def head(X):
        """Head algorithm for phrase structure objects"""
        return next((x for x in (X,) + X.const if x.zero_level()), X.phrasal() and X.right().head())

    def Merge(X, Y):
        """Standard Merge"""
        return PhraseStructure(X, Y)

    def MergePreconditions(X, Y):
        """Preconditions for Merge"""
        return not Y.bound_morpheme() and \
               not X.selection_violation(Y) and X.sandwich_condition(Y)

    def sandwich_condition(X, Y):
        """Checks that a specifier condition is satisfied inside complement
        before Merge"""
        if X.zero_level() and \
                {f for f in Y.head().features if
                 fformat(f)[0] == '+SPEC' and
                 'Ø' not in f and
                 ':X' not in f}:
            return Y.phrasal() and Y.left().phrasal()
        return True

    def selection_violation(X, Y):
        """Selection violation for both complement and specifier selection"""
        def satisfy(X, fset):
            return (not X and 'Ø' in fset) or (X and fset & X.head().features)

        return {f for x in X.copy().Merge(Y.copy()).const for f in x.features if
                fformat(f)[0] == '+COMP' and not satisfy(x.complement(), fformat(f)[1])} or \
               (X.phrasal() and {f for f in Y.head().features if
                                 fformat(f)[0] == '+SPEC' and not satisfy(X, fformat(f)[1])})

    def MergeComposite(X, Y):
        """Composite Merge operation contains head and phrasal movements (if applicable) and Merge"""
        return {X.HeadMovement(Y).Merge(Y).phrasal_movement()}

    def Adjoin(X, Y):
        """Adjunction is motherhood without corresponding daughter dependency"""
        X.set_mother(Y)
        return {X, Y}

    def AdjoinPreconditions(X, Y):
        """Preconditions for adjunction are that X is not an adjunct,
        Y is a phrasal root constituent (no countercyclic adjunction) and X has a feature
        licensing the operation"""
        return not X.mother() and not Y.mother() and Y.phrasal() and X.adjoins_to(Y)

    def adjoins_to(X, Y):
        """Checks that X has a feature [adjoin:F] licensing adjunction to Y with feature [F]"""
        fset = {f.split(':')[1] for f in X.head().features if f.startswith('adjoin:')}
        return fset and fset <= Y.head().features

    def adjunct(X):
        """Checks if X is an adjunct"""
        return X.mother() and X not in X.mother().const

    def HeadMovementPreconditions(X, Y):
        """Preconditions for Head Movement after [X Y] are that
        X must be zero-level object and a bound morpheme"""
        return X.zero_level() and X.bound_morpheme()

    def bound_morpheme(X):
        """Definition for bound morpheme is that X has w-selection features"""
        return X.wcomplement_features()

    def HeadMovement(X, Y):
        """Head movement after [X Y] copies the head of Y and Head Merges it to X"""
        if X.HeadMovementPreconditions(Y):
            PhraseStructure.log_report += f'Head movement by {X}° targeting {Y.head()}°'
            return Y.head().chaincopy().HeadMerge(X)
        return X

    def HeadMergePreconditions(X, Y):
        """Preconditions for Head Merge (X Y) are that both X and Y are zero-level objects,
        Y w-selects X and HM is licensed at X by feature [ε]"""
        return X.zero_level() and Y.zero_level() and \
               Y.w_selects(X) and 'ε' in X.features

    def HeadMerge(X, Y):
        """Creates a zero-level object from two zero-level objects.
        Features of the resulting object are inherited from the rightmost
        constituent"""
        Z = X.Merge(Y)
        Z.zero = True
        Z.features = Y.features - {f for f in Y.features if f.startswith('!wCOMP:')}
        return Z

    def phrasal_movement(X):
        """Induces both phrasal A- and A-bar movement if applicable"""
        return X.phrasal_A_bar_movement().phrasal_A_movement()

    def phrasal_A_movement(X):
        """Simple algorithm for phrasal A-movement with preconditions"""
        if X.left().EPP() and \
                X.left().complement() and \
                X.left().complement().goal_for_A_movement():
            PhraseStructure.log_report += f'\nPhrasal A-movement by ' \
                                          f'{X.left()} targeting ' \
                                          f'{X.left().complement().goal_for_A_movement()}\n'
            return X.left().complement().goal_for_A_movement().chaincopy().Merge(X)
        return X

    def phrasal_A_bar_movement(X):
        """Simple algorithm for phrasal Ā-movement with preconditions"""
        if X.left().operator() and X.left().complement().minimal_search("wh"):
            PhraseStructure.log_report += f'\nPhrasal A-bar movement by ' \
                                          f'{X.left()} targeting ' \
                                          f'{X.left().complement().minimal_search("wh")}\n'
            return X.left().complement().minimal_search('wh').chaincopy().Merge(X)
        return X

    def operator(X):
        """Abstraction for the property of being an operator"""
        return 'wh' in X.features

    def referential(X):
        """Abstraction for the property of being referential"""
        return 'D' in X.head().features

    def EPP(X):
        """Abstraction for the property of EPP"""
        return 'EPP' in X.features

    def target_for_A_movement(X):
        return next((x for x in [X.left(), X.right()] if x.phrasal() and x.referential()), None)

    def minimal_search(X, feature):
        """Searches downstream for an element with [feature].
        The algorithm follows labeling and head-complement relations.
        """
        while X:
            if X.zero_level():
                X = X.complement()
            else:
                for x in X.const:
                    if feature in x.head().features:
                        return x
                    if x.head() == X.head():
                        X = x

    def w_selects(Y, X):
        """Word-internal selection between X and Y under (X Y), where Y selects for X"""
        return Y.wcomplement_features() and \
               Y.wcomplement_features() <= X.features

    def wcomplement_features(X):
        """Returns a set of w-selection features"""
        return {f.split(':')[1] for f in X.features if f.startswith('!wCOMP')}

    def zero_level(X):
        """Abstraction for the notion of zero-level object"""
        return X.zero

    def phrasal(X):
        return not X.zero_level()

    def linearize(X):
        """Linearizes phrase structure objects into sentences"""
        if X.elliptic:
            return ''
        if X.zero_level():
            return X.linearize_word()[:-1] + ' '
        return ''.join([x.linearize() for x in X.const])

    def linearize_word(X):
        """Separate linearization algorithm for words"""
        if X.terminal():
            return X.phonological_exponent + '#'
        return ''.join([x.linearize_word() for x in X.const])

    def terminal(X):
        return len({x for x in X.const if x}) == 0

    def __str__(X):
        """Simple printout function for phrase structure objects"""
        if X.elliptic:
            return '__' + X.get_chain_subscript()
        if X.terminal():
            return X.phonological_exponent
        elif X.zero_level():
            return '(' + ' '.join([f'{x}' for x in X.const]) + ')'
        return '[' + ' '.join([f'{x}' for x in X.const]) + ']' + X.get_chain_subscript()

    def get_chain_subscript(X):
        if X.chain_index != 0:
            return ':' + str(X.chain_index)
        return ''

    def clean_chains(X):
        def collapse_chain_indexes(X, d, n):
            if X.chain_index > 0 and str(X.chain_index) not in d.keys():
                d[str(X.chain_index)] = n
                n += 1
            if X.phrasal():
                collapse_chain_indexes(X.left(), d, n)
                collapse_chain_indexes(X.right(), d, n)

        def prune_chain_indexes(X, d):
            if X.chain_index:
                X.chain_index = d[str(X.chain_index)]
            if X.phrasal():
                prune_chain_indexes(X.left(), d)
                prune_chain_indexes(X.right(), d)
        d = {}
        collapse_chain_indexes(X, d, 1)
        prune_chain_indexes(X, d)

    def lexical_category(X):
        return next((f for f in ['N', 'v', 'v*', 'Adv', 'Inf', 'V', 'C', 'D', 'A', 'P', 'T', 'a', 'b', 'c'] if f in X.features), '?')


N_sentences = 0
data = set()

def derive(sWM):
    """Wrapper for the derivation_search_function"""
    global N_sentences
    global data
    N_sentences = 0
    data = set()
    print('\nNumeration: {'+ ', '.join((str(x) for x in sWM)) + '}\n')
    derivational_search_function(sWM)
    for i, s in enumerate(data, start=1):
        print_(f'{i}.\n{s} ')

def collapse_and_linearize(sWM):
    """Collapses adjuncts into the phrase structure and begins linearization"""
    for X in [x for x in sWM if x.adjunct()]:
        X.mother().const += (X,)
        sWM.remove(X)
    X = sWM.pop()
    return X, X.linearize()

def print_lst(SO):
    return ', '.join([str(x) for x in SO])

def print_(s):
    """Prints for console and log file"""
    print(s)
    PhraseStructure.log_report += s

def print_sWM(sWM):
    aWM = [f'{x}' for x in sWM if not x.adjunct()]
    iWM = [f'{x.mother().head().lexical_category()}P|{x}' for x in sWM if x.adjunct()]
    s = f'{", ".join(aWM)}'
    if iWM:
        s += f' {{ {", ".join(iWM)} }}'
    return s

syntactic_operations = [(PhraseStructure.MergePreconditions, PhraseStructure.MergeComposite, 2, 'Merge'),
                        (PhraseStructure.AdjoinPreconditions, PhraseStructure.Adjoin, 2, 'Adjoin'),
                        (PhraseStructure.HeadMergePreconditions, PhraseStructure.HeadMerge, 2, 'Head Merge')]

# Copies the contents of sWM for backtracking purposes
def sWMcopy(sWM, SO):
    def get_mirror(x, M):
        return next((m[1] for m in M if x == m[0]), None)

    M = [(x, x.copy()) for x in sWM]
    # Mirror horizontal adjunct dependencies
    for m in M:
        if m[0].adjunct():
            m[1].mother_ = get_mirror(m[0].mother(), M)
    SO_ = [get_mirror(x, M) for x in SO]    #   Selected objects in the new sWM
    sWM_ = [x[1] for x in M if x[1] not in SO_]
    return set(sWM_), tuple(SO_)

def derivational_search_function(sWM):
    PhraseStructure.log_report += f'= {print_sWM(sWM)}\n'
    if derivation_is_complete(sWM):
        process_final_output(sWM)
    else:
        for Preconditions, OP, n, name in syntactic_operations:
            for SO in itertools.permutations(sWM, n):
                if Preconditions(*SO):
                    PhraseStructure.log_report += f'\n{name}({print_lst(SO)})\n'
                    sWM_, SO_ = sWMcopy(sWM, SO)
                    derivational_search_function(sWM_ | (OP(*SO_)))
            PhraseStructure.log_report += '.'

def derivation_is_complete(sWM):
    return len([X for X in sWM if not X.mother()]) == 1

def process_final_output(sWM):
    global N_sentences
    global data
    N_sentences += 1
    for x in sWM:
        x.clean_chains()
    data_str = print_sWM(sWM) + '\n'
    L, output_sentence = collapse_and_linearize(sWM)
    data_str += f'{L}\n{output_sentence}\n'
    PhraseStructure.chain_index = 0
    data.add(data_str)

Lex = Lexicon()

Numeration_lst = [['the', 'dog', 'ed', 'bark'],
                  ['the', 'dog', 'does', 'bark'],
                  ['the', 'man', 'was', 'en', 'bite'],
                  ['the', 'dog', 'T', 'seem', 'to', 'bark'],
                  ['the', 'dog', 'ed', 'v', 'bite', 'the', 'man'],
                  ['the', 'dog', 'does', 'v', 'bite', 'the', 'man'],
                  ['C(wh)', 'the', 'dog', 'does', 'bark'],
                  ['C(wh)', 'which', 'dog', 'does', 'bark'],
                  ['C(wh)', 'which', 'dog', 'does', 'v', 'bite', 'the', 'man'],
                  ['the', 'dog', 'ed', 'bark', 'frequently'],
                  ['the', 'dog', 'ed', 'bark', 'frequently', 'frequently'],
                  ['the', 'dog', 'T', 'seem', 'to', 'bark', 'frequently'],
                  ['the', 'man', 'was', 'en', 'bite', 'frequently'],
                  ['the', 'dog', 'ed', 'v', 'bite', 'the', 'man', 'frequently'],
                  ['C(wh)', 'which', 'dog', 'does', 'bark', 'frequently']]

log_file = open('log.txt', 'w')

for numeration in Numeration_lst:
    PhraseStructure.log_report = '\n\n=====\nNumeration: {' + ', '.join(numeration) + '}\n'
    derive({Lex.retrieve(word) for word in numeration})
    log_file.write(PhraseStructure.log_report)
