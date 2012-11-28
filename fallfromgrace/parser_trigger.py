# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import logging
import ply.lex as lex
import ply.yacc as yacc

import fallfromgrace.number as number

log = logging.getLogger('fall-from-grace')


tokens = ('VAR', 'NUMBER', 'OP1', 'OP2')

t_VAR = r'(rmem|vmem)'
t_OP1 = r'(<|>)'
t_OP2 = r'(<=|>=|==)'

def t_NUMBER(t):
    r'[0-9\.]+[kmgKMG]?'
    try:
        t.value = number.unfix(t.value, {
                'k': 1024,
                'm': 1024**2,
                'g': 1024**3})
    except ValueError:
        log.error('Integer value too large %d', t.value)
        t.value = 0
    return t

t_ignore = " \t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    log.error('Illegal character "%s"', t.value[0])
    raise Exception('Illegal character "%s"' % (t.value[0],))
    t.lexer.skip(1)

lexer = lex.lex(errorlog=log)

precedence = (
    ('left', 'OP2', 'OP1'),
    )

names = {}

def p_statement_expr(t):
    'statement : expression'
    t[0] = t[1]

def p_expression_binop(t):
    '''expression : expression OP2 expression
                  | expression OP1 expression'''
    t[0] = (t[1], t[2], t[3])

def p_expression_number(t):
    '''expression : NUMBER'''
    t[0] = t[1]

def p_expression_var(t):
    'expression : VAR'
    t[0] = t[1]

def p_error(t):
    log.error('Syntax error at "%s"', t.value)
    raise Exception('Syntax error at "%s"' % (t.value,))

parser = yacc.yacc(errorlog=log,
                   outputdir='/tmp',
                   debugfile='/tmp/parser_trigger.out')

def parse(s):
    """Parse a rule specification.
    """

    parsed = parser.parse(s, lexer=lexer)
    if len(parsed) != 3:
        raise ValueError('parsed incorrectly: %s' % (parsed,))
    return parsed
