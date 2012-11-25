# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Björn Edström <be@bjrn.se>
# See LICENSE for details.

import logging
import ply.lex as lex
import ply.yacc as yacc

import fallfromgrace.number as number

log = logging.getLogger('fall-from-grace')

tokens = ('TERM', 'KILL', 'EXEC', 'AT', 'NUMBER', 'PROGRAM')

t_TERM = r'term'
t_KILL = r'kill'
t_AT = r'[@]'
t_EXEC = r'exec'
t_PROGRAM = r'.+'

def t_NUMBER(t):
    r'\d+[smh]?'
    try:
        t.value = number.unfix(t.value, {
                's': 1,
                'm': 60,
                'h': 60**2})
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
    ('left', 'AT', 'NUMBER', 'PROGRAM'),
    )

def p_statement_expr(t):
    'statement : expression'
    t[0] = t[1]

def p_expression_action(t):
    '''expression : TERM
                  | KILL
                  | EXEC AT NUMBER PROGRAM
                  | EXEC PROGRAM'''
    t[0] = t[1:]

def p_error(t):
    log.error('Syntax error at "%s"', t.value)
    raise Exception('Syntax error at "%s"' % (t.value,))

parser = yacc.yacc(errorlog=log,
                   outputdir='/tmp',
                   debugfile='/tmp/parser_action.out')

def parse(s):
    """Parse an action specification.
    """

    parsed = parser.parse(s, lexer=lexer)
    if not parsed:
        raise ValueError('parse error: failed to parse action')
    return parsed
