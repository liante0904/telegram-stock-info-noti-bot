CREATE OR REPLACE FUNCTION set_ds_share_telegram_url()
RETURNS trigger AS $$
BEGIN
    IF NEW."SEC_FIRM_ORDER" = 11
       AND (NEW."TELEGRAM_URL" IS NULL OR NEW."TELEGRAM_URL" = '') THEN
        NEW."TELEGRAM_URL" := 'https://ssh-oci.netlify.app/share?id=' || NEW.report_id::text;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_ds_share_telegram_url ON "TB_SEC_REPORTS";

CREATE TRIGGER trg_set_ds_share_telegram_url
BEFORE INSERT OR UPDATE ON "TB_SEC_REPORTS"
FOR EACH ROW
EXECUTE FUNCTION set_ds_share_telegram_url();
