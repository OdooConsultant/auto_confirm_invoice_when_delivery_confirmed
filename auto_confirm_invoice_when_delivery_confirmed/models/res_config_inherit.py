

from odoo import api, fields, models, _

class ConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"


    auto_send_mail_invoice = fields.Boolean("Auto Send Mail Invoice", config_parameter='auto_send_mail_invoice')
    auto_validate_invoice = fields.Boolean("Auto Validate Invoice", config_parameter='auto_validate_invoice')
    

    # auto_send_mail_invoice = fields.Boolean("Auto Send Mail Invoice")
    # auto_validate_invoice = fields.Boolean("Auto Validate Invoice")
    #
    #
    #
    # def get_values(self):
    #     res = super(ConfigSettings, self).get_values()
    #     auto_send_mail_invoice = self.env['ir.config_parameter'].sudo().get_param('bi_auto_invoice_delivery.auto_send_mail_invoice')
    #     auto_validate_invoice = self.env['ir.config_parameter'].sudo().get_param('bi_auto_invoice_delivery.auto_validate_invoice')
    #     res.update(
    #         auto_send_mail_invoice = auto_send_mail_invoice,
    #         auto_validate_invoice = auto_validate_invoice,
    #     )
    #     return res
    #
    # def set_values(self):
    #     super(ConfigSettings, self).set_values()
    #     self.env['ir.config_parameter'].sudo().set_param('bi_auto_invoice_delivery.auto_send_mail_invoice', self.auto_send_mail_invoice)
    #     self.env['ir.config_parameter'].sudo().set_param('bi_auto_invoice_delivery.auto_validate_invoice', self.auto_validate_invoice)

