import itertools

lexicon = {'a': {'a'}, 'b': {'b'}, 'c': {'c'}, 'd': {'d'},
           'the': {'D'},
           'dog': {'N'},
           'bark': {'V', 'V/INTR'},
           'ing': {'N', '!wCOMP:V', 'ε'},
           'man': {'N'},
           'bite': {'V', 'V/TR'},
           'v': {'v', 'V'},
           'does': {'T', 'Aux'},
           'ed': {'T', '!wCOMP:V'}
           }

lexical_redundancy_rules = {'D': {'+COMP:N', '+SPEC:Ø'},
                            'V/TR': {'+COMP:D', '+SPEC:X'},
                            'V/INTR': {'+SPEC:Ø,X', '+COMP:D'},
                            'T': {'+COMP:V'},
                            'v': {'+COMP:V', '+SPEC:D', '!wCOMP:V'},
                            'N': {'+COMP:Ø', '+SPEC:Ø'}}


def fformat(f):
    if f.startswith('+COMP') or f.startswith('+SPEC'):
        return f.split(':')[0], set(f.split(':')[1].split(','))
    return None, None

# Class which stores and maintains the lexicon
class Lexicon:
    def __init__(self):
        self.lexical_entries = dict()
        self.compose_lexicon()

    # Composes the lexicon from the list of words and lexical redundancy rules
    def compose_lexicon(self):
        for lex in lexicon.keys():
            self.lexical_entries[lex] = lexicon[lex]
            for trigger_feature in lexical_redundancy_rules:
                if trigger_feature in self.lexical_entries[lex]:
                    self.lexical_entries[lex] = self.lexical_entries[lex] | lexical_redundancy_rules[trigger_feature]

    # Retrieves lexical items from the lexicon and wraps them into zero-level
    # phrase structure objects
    def retrieve(self, name):
        X0 = PhraseStructure()
        X0.features = self.lexical_entries[name]        # Retrieves lexical features from the lexicon
        X0.zero = True                                  # True = zero-level category
        X0.phonological_exponent = name                 # Spellout form is the same as the name
        return X0

class PhraseStructure:
    log_report = ''
    def __init__(self, X=None, Y=None):
        self.const = (X, Y)       			# Left and right daughter constituents, in an ordered tuple
        self.features = set()     			# Lexical features (not used in this script), in a set
        self.mother_ = None        			# Mother node (not used in this script)
        if X:
            X.mother_ = self
        if Y:
            Y.mother_ = self
        self.zero = False
        self.phonological_exponent = ''
        self.elliptic = False

    def copy(X):
        if not X.terminal():
            Y = PhraseStructure(X.left().copy(), X.right().copy())
        else:
            Y = PhraseStructure()
        Y.copy_properties(X)
        return Y

    def copy_properties(Y, X):
        Y.phonological_exponent = X.phonological_exponent
        Y.features = X.features.copy()
        Y.elliptic = X.elliptic
        Y.zero = X.zero

    # Grammatical copying with phonological silencing
    def chaincopy(X):
        Y = X.copy()
        X.elliptic = True
        return Y

    # Mother-of relation
    def mother(X):
        return X.mother_

    def left(X):
        return X.const[0]

    def right(X):
        return X.const[1]

    def isLeft(X):
        return X.mother() and X.mother().left() == X

    def isRight(X):
        return X.mother() and X.mother().right() == X

    # Determines whether X has a sister constituent and returns that constituent if present
    def sister(X):
        if X.isLeft():
            return X.mother().right()
        return X.mother().left()

    # Complement is right sister of a zero-level object
    def complement(X):
        if X.zero_level() and X.isLeft():
            return X.sister()

    # Standard Merge
    def Merge(X, Y):
        return PhraseStructure(X, Y)

    # Preconditions for Merge
    def MergePreconditions(X, Y):
        return not Y.bound_morpheme() and \
               not X.selection_violation(Y)

    def MergeComposite(X, Y):
        return X.HeadMovement(Y).Merge(Y)

    def HeadMovementPreconditions(X, Y):
        return X.zero_level() and \
               X.bound_morpheme()

    def bound_morpheme(X):
        return X.wcomplement_features()

    # Head movement
    def HeadMovement(X, Y):
        if X.HeadMovementPreconditions(Y):
            PhraseStructure.log_report += f'\nHead chain by {X}° targeting {Y.head()}° + '
            return Y.head().chaincopy().HeadMerge(X)
        return X

    def selection_violation(X, Y):
        def satisfy(X, fset):
            return (not X and 'Ø' in fset) or (X and fset & X.head().features)

        return {f for x in X.Merge(Y).const for f in x.features if
                fformat(f)[0] == '+COMP' and not satisfy(x.complement(), fformat(f)[1])} or \
               (X.phrasal() and {f for f in Y.head().features if
                                 fformat(f)[0] == '+SPEC' and not satisfy(X, fformat(f)[1])})

    # Preconditions for Head Merge (X Y)
    def HeadMergePreconditions(X, Y):
        return X.zero_level() and \
               Y.zero_level() and \
               Y.w_selects(X) and 'ε' in X.features

    # Head Merge creates zero-level categories and implements feature inheritance
    def HeadMerge(X, Y):
        Z = X.Merge(Y)
        Z.zero = True
        Z.features = Y.features - {f for f in Y.features if f.startswith('!wCOMP:')}
        return Z

    # Word-internal selection between X and Y under (X Y),
    # where Y selects for X
    def w_selects(Y, X):
        return Y.wcomplement_features() and \
               Y.wcomplement_features() <= X.features

    # Returns a set of w-selection features
    def wcomplement_features(X):
        return {f.split(':')[1] for f in X.features if f.startswith('!wCOMP')}

    # Interface function for zero
    def zero_level(X):
        return X.zero

    def phrasal(X):
        return not X.zero_level()

    # Maps phrase structure objects into linear lists of words
    def linearize(X):
        if X.elliptic:
            return ''
        output_str = ''
        if X.zero_level():
            output_str += X.linearize_word('') + ' '
        else:
            for x in X.const:
                output_str += x.collapse_and_linearize()
        return output_str

    # Spellout algorithm for words, creates morpheme boundaries marked by symbol
    def linearize_word(X, word_str):
        if X.terminal():
            if word_str:
                word_str += '#'
            word_str += X.phonological_exponent
        else:
            for x in X.const:
                word_str = x.linearize_word(word_str)
        return word_str

    # Terminal elements do not have daughter constituents
    def terminal(X):
        return len({x for x in X.const if x}) == 0
         
    # Calculates the head of any phrase structure object
    def head(X):
        for x in (X,) + X.const:
            if x and x.zero_level():
                return x
        return x.head()

    # Printout function for phrase structure objects
    def __str__(X):
        if X.elliptic:
            return '__'
        output_str = ''
        if X.terminal():
            output_str += X.phonological_exponent
        else:
            if X.zero_level():
                brackets = ('(', ')')
            else:
                brackets = ('[', ']')
            output_str += brackets[0]
            if not X.zero_level():
                output_str += f'_{X.head().lexical_category()}P '
            for const in X.const:
                output_str += f'{const}'
                if const.isLeft():
                    output_str += f' '
            output_str += brackets[1]
        return output_str

    # Defines the major lexical categories used in all printouts
    def lexical_category(X):
        return next((f for f in ['N', 'v', 'V', 'D', 'A', 'P', 'T', 'a', 'b', 'c'] if f in X.features), '?')


syntactic_operations = [(PhraseStructure.MergePreconditions, PhraseStructure.MergeComposite, 2, 'Merge'),
                        (PhraseStructure.HeadMergePreconditions, PhraseStructure.HeadMerge, 2, 'Head Merge')]
N_sentences = 0
data = set()

def derive(sWM):
    global N_sentences
    global data
    N_sentences = 0
    data = set()
    print('\nNumeration: {'+ ', '.join((str(x) for x in sWM)) + '}\n')
    derivational_search_function(sWM)
    for i, s in enumerate(data, start=1):
        print_(f'{i}. {s} ')

def wcopy(sWM):
    return (x.copy() for x in sWM)

def print_lst(SO):
    return ', '.join([str(x) for x in SO])

def print_(s):
    print(s)
    PhraseStructure.log_report += s

def derivational_search_function(sWM):
    if derivation_is_complete(sWM):
        process_final_output(sWM)
    else:
        for Preconditions, OP, n, name in syntactic_operations:
            for SO in itertools.permutations(sWM, n): 
                if Preconditions(*SO):
                    new_sWM = {x for x in sWM if x not in set(SO)} | {OP(*wcopy(SO))}
                    PhraseStructure.log_report += f'\n{name}({print_lst(SO)})\n= ({print_lst(new_sWM)})\n\n'
                    derivational_search_function(new_sWM)

def derivation_is_complete(sWM):
    return len(sWM) == 1

def process_final_output(sWM):
    global N_sentences
    global data
    N_sentences += 1
    result = sWM.pop()
    data.add(f'{result.collapse_and_linearize()} // {result}')
    PhraseStructure.log_report += f'\t{N_sentences}. {result.collapse_and_linearize()} // {result}\n'


Lex = Lexicon()

Numeration_lst = [['the', 'dog', 'ed', 'v', 'bite', 'the', 'man']]
log_file = open('log.txt', 'w')

for numeration in Numeration_lst:
    PhraseStructure.log_report = '\n\n=====\nNumeration: {' + ', '.join(numeration) + '}\n'
    derive({Lex.retrieve(word) for word in numeration})
    log_file.write(PhraseStructure.log_report)
