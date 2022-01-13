

from odoo import api, fields, models, _
from odoo.tools.misc import formatLang, format_date, get_lang

from json import dumps
import ast
import json
import re

    
    
class AutoReconsile(models.Model):
    _name = 'auto.reconsile'
    
    main_move_id = fields.Many2one('account.move','Move')
    move_id = fields.Many2one('account.move','Move')
    amount = fields.Float('Amount')
    line_id = fields.Many2one('account.move.line', 'Move Line')
    
    
    
    
    