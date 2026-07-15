# -*- coding: utf-8 -*-
from odoo import models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _migrate_local_to_cloud_storage(self, session):
        """Allow the official migration to change only the storage backend.

        ``account`` protects PDF/XML attachments of posted moves by rejecting
        writes to ``raw``.  The cloud migration clears ``raw`` only after the
        same payload has been uploaded successfully, so let the audit-trail
        check distinguish this storage transition from content removal.
        """
        attachment = self.with_context(
            sultan_cloud_storage_backend_migration=True,
        )
        return super(IrAttachment, attachment)._migrate_local_to_cloud_storage(
            session,
        )

    def _except_audit_trail(self):
        if self.env.context.get("sultan_cloud_storage_backend_migration"):
            return
        return super()._except_audit_trail()

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
