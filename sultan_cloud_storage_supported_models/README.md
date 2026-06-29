# Sultan Cloud Storage Supported Models

This Odoo 19 addon allows selected models to use Odoo cloud storage for
attachments by removing them from `ir.attachment` cloud-storage unsupported
models.

## Configuration

The default allow-list is stored in this system parameter:

```text
sultan_cloud_storage_supported_models.supported_models
```

Edit it from **Settings > Technical > Parameters > System Parameters**.
Values can be comma-separated or one model per line.

The module keeps Odoo's unsupported list intact except for the models listed in
that parameter.

## Validation

After installing or upgrading the module, verify from an Odoo shell:

```python
unsupported = env["ir.attachment"]._get_cloud_storage_unsupported_models()
len(unsupported), sorted(unsupported)
```

Remove any model from the system parameter if its attachment workflow does not
work correctly with Google Cloud Storage.
