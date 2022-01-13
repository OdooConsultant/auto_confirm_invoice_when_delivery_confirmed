

from odoo import api, fields, models, _
from odoo.tools.misc import formatLang, format_date, get_lang

from json import dumps
import ast
import json
import re


class Picking(models.Model):
    _inherit = "stock.picking"

    @api.depends('state')
    def _get_invoiced(self):
        for order in self:
            invoice_ids = self.env['account.move'].sudo().search([('picking_id','=',order.id)])
            order.invoice_count = len(invoice_ids)
    invoice_count = fields.Integer(string='# of Invoices', compute='_get_invoiced')
    
    def button_view_invoice(self):
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        work_order_id = self.env['account.move'].sudo().search([('picking_id', '=', self.id)])
        inv_ids = []
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        context = {
            'default_move_type': work_order_id[0].move_type,
        }
        action['domain'] = [('id', 'in', work_order_id.ids)]
        action['context'] = context
        return action

    
    def _action_done(self):
        action = super(Picking, self)._action_done()
        res_config = self.env['res.config.settings'].sudo().search([],order="id desc", limit=1)
        
        get_param = self.env['ir.config_parameter'].sudo().get_param
        auto_validate_invoice = get_param('auto_validate_invoice')
        auto_send_mail_invoice = get_param('auto_send_mail_invoice')
        
        
        
        for picking in self:
        
            if picking.state == 'done':            
    
                if picking.picking_type_id.code == 'outgoing':
                    if picking.origin:
                        pass
                    else:
                        picking.update({'origin': picking._context.get('default_origin')})   
                    inv_obj = self.env['account.move']
                    invoice_lines =[]
                    invoice_vals = []
                    sale_order_line_obj = self.env['account.move.line']
                    sale_order  =  self.env['sale.order'].search([('name', '=',picking.origin )])
                    journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
                    if not journal:
                        raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (picking.company_id.name, picking.company_id.id))
    
                    if sale_order:
                        
                        inv_vals = {
                                'invoice_origin': picking.origin,
                                'picking_id':picking.id,
                                'move_type': 'out_invoice',
                                'ref': False,
                                'sale_id':sale_order.id,
                                'journal_id': journal.id,  
                                'partner_id': sale_order.partner_invoice_id.id,
                                'currency_id': sale_order.pricelist_id.currency_id.id,
                                'invoice_payment_term_id': sale_order.payment_term_id.id,
                                'fiscal_position_id': sale_order.fiscal_position_id.id or sale_order.partner_id.property_account_position_id.id,
                                'team_id': sale_order.team_id.id,
                                'invoice_date' : fields.Datetime.now().date(),
                            }
                        
                        if 'l10n_in_gst_treatment' in sale_order._model_fields and sale_order.l10n_in_company_country_code == 'IN':
                            inv_vals['l10n_in_reseller_partner_id'] = sale_order.l10n_in_reseller_partner_id.id
                            if sale_order.l10n_in_journal_id:
                                inv_vals['journal_id'] = sale_order.l10n_in_journal_id.id
                                inv_vals['l10n_in_gst_treatment'] = sale_order.l10n_in_gst_treatment
                            
                        if sale_order.partner_shipping_id:
                            inv_vals['partner_shipping_id'] = sale_order.partner_shipping_id.id
                            
                        if sale_order.note:
                            inv_vals['narration'] = sale_order.note
                            
                        if sale_order.client_order_ref:
                            inv_vals['ref'] = sale_order.client_order_ref
                            
                            
                        invoice = inv_obj.create(inv_vals)
                        
                        for so_line in  sale_order.order_line :
                            if so_line.product_id.type == "service":
                                if so_line.product_uom_qty != so_line.qty_invoiced:
                                    if so_line.product_id.property_account_income_id:
                                        account_id = so_line.product_id.property_account_income_id
                                    elif so_line.product_id.categ_id.property_account_income_categ_id:
                                        account_id = so_line.product_id.categ_id.property_account_income_categ_id
                                    elif journal.default_account_id:
                                        account_id = journal.default_account_id
                                    else:
                                        raise UserError(_('Please define an account for the Product/Category.'))
                                    inv_line = {
                                            'name': so_line.name,
                                            'product_id': so_line.product_id.id,
                                            'product_uom_id': so_line.product_id.uom_id.id,
                                            'quantity': so_line.product_uom_qty,
                                            'account_id': account_id.id,
                                            'display_type': so_line.display_type,
                                            'tax_ids': [(6, 0, so_line.tax_id.ids)],
                                            'move_id':invoice.id,
                                            'price_unit': so_line.price_unit,
                                            'sale_line_ids': [(4, so_line.id)],
                                            }
                                    invoice_vals.append((0,0,inv_line))
                                    so_line.write({
                                        'qty_to_invoice':so_line.product_uom_qty
                                    })                                
                            else:
                                if so_line.product_id.property_account_income_id:
                                    account = so_line.product_id.property_account_income_id
                                elif so_line.product_id.categ_id.property_account_income_categ_id:
                                    account = so_line.product_id.categ_id.property_account_income_categ_id
                                else:
                                    account = self.env['ir.property']._get('property_account_income_categ_id', 'product.category')
                                
                                if not account:
                                    raise UserError(_('Please define an account for the Product/Category.'))
        
                                route = self.env['stock.location.route'].search([('name','=','Dropship')])
                                if self._context.get('flag') == True and route.id in so_line.product_id.route_ids.ids:
                                    pass
                                
                                else:
                                    if so_line.product_id.invoice_policy == 'delivery':  
                                        inv_line = {
                                                'name': so_line.name,
                                                'product_id': so_line.product_id.id,
                                                'product_uom_id': so_line.product_uom.id,
                                                'quantity': so_line.qty_to_invoice,
                                                'account_id': account.id,
                                                'display_type': so_line.display_type,
                                                'tax_ids': [(6, 0, so_line.tax_id.ids)],
                                                'move_id':invoice.id,
                                                'price_unit': so_line.price_unit,
                                                'sale_line_ids': [(4, so_line.id)],
                                                }
                                        
                                        invoice_vals.append((0,0,inv_line))
                                        so_line.write({'qty_to_invoice':so_line.product_uom_qty})
                                    else:
                                        inv_line = {
                                                'name': so_line.name,
                                                'product_id': so_line.product_id.id if not so_line.display_type else False,
                                                'product_uom_id': so_line.product_uom.id,
                                                'quantity': so_line.product_uom_qty if not so_line.display_type else False,
                                                'account_id': account.id if not so_line.display_type else False,
                                                'display_type': so_line.display_type,
                                                'tax_ids': [(6, 0, so_line.tax_id.ids)],
                                                'move_id':invoice.id,
                                                'price_unit': so_line.price_unit if not so_line.display_type else False,
                                                'sale_line_ids': [(4, so_line.id)],
                                                }
                                         
                                        invoice_vals.append((0,0,inv_line))
                                    
                                    if so_line.discount:
                                        inv_line['discount'] = so_line.discount
                                    
                        invoice.write({
                            'invoice_line_ids' : invoice_vals
                        })
                        is_reconsile = False
                        if auto_validate_invoice == True  or auto_validate_invoice == 'True':
                            invoice.action_post()
                            if invoice.invoice_has_outstanding:
                                if invoice.reconsile_custom_ids:
                                    for i in invoice.reconsile_custom_ids:
                                        if i.amount >= invoice.amount_residual:
                                            lines = i.line_id
                                            lines += invoice.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                                            lines.reconcile()
                                            is_reconsile = True
                                            break
                                        else:
                                            continue
                            
                        if (auto_validate_invoice == True or auto_validate_invoice == 'True') and (auto_send_mail_invoice == True or auto_send_mail_invoice == 'True') and is_reconsile == False:
                                
                            template = self.env.ref('account.email_template_edi_invoice', False)
                            if invoice.partner_id.email:
                                send = invoice.with_context(force_send=True,model_description='Invoice').message_post_with_template(int(template),email_layout_xmlid="mail.mail_notification_paynow")
                                
                        if invoice.reconsile_custom_ids:
                            invoice.reconsile_custom_ids.unlink()
        return action
    
    
