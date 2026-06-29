# -*- coding: utf-8 -*-
from odoo import models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _get_cloud_storage_unsupported_models(self):
        unsupported_models = super()._get_cloud_storage_unsupported_models()
        supported_models = self._get_sultan_cloud_storage_supported_models()

        if isinstance(unsupported_models, set):
            return unsupported_models - supported_models

        return [
            model
            for model in unsupported_models
            if model not in supported_models
        ]

    def _get_sultan_cloud_storage_supported_models(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "sultan_cloud_storage_supported_models.supported_models",
            "",
        )
        return {
            model.strip()
            for model in value.replace("\n", ",").split(",")
            if model.strip()
        }
