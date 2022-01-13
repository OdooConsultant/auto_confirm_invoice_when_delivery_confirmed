

from odoo import api, fields, models, _
from odoo.tools.misc import formatLang, format_date, get_lang

from json import dumps
import ast
import json
import re


class AccountInvoice(models.Model):
    _inherit = "account.move"

    picking_id = fields.Many2one('stock.picking','Picking')
    sale_id  =  fields.Many2one('sale.order', 'Sale Origin')



    reconsile_custom_ids = fields.Many2many('auto.reconsile', 'auto_reconsile_rel', 'reconsile_custom_id', 'move_id', string='Reconsile Custom',)
    
    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = json.dumps(False)
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('move_id.state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            all_records = []
            
            for line in self.env['account.move.line'].search(domain):

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = move.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency': move.currency_id.symbol,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'position': move.currency_id.position,
                    'digits': [69, move.currency_id.decimal_places],
                    'payment_date': fields.Date.to_string(line.date),
                })
                
                
                vals_custom_for_reconsile = {'move_id': line.move_id.id, 'amount':amount, 'main_move_id': move.id, 'line_id': line.id}
                reconsile_record = self.env['auto.reconsile'].create(vals_custom_for_reconsile)
                all_records.append(reconsile_record)

                
            if all_records:
                move.reconsile_custom_ids = [i.id for i in all_records]

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = json.dumps(payments_widget_vals)
            move.invoice_has_outstanding = True
            
            
    