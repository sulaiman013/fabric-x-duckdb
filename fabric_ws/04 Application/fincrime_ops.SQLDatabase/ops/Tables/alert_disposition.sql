CREATE TABLE [ops].[alert_disposition] (
    [disposition_id] BIGINT         IDENTITY (1, 1) NOT NULL,
    [alert_id]       VARCHAR (64)   NOT NULL,
    [_mirror_row_id] BIGINT         NOT NULL,
    [disposition]    VARCHAR (32)   NOT NULL,
    [reason]         NVARCHAR (512) NULL,
    [analyst]        NVARCHAR (256) NOT NULL,
    [decided_at]     DATETIME2 (3)  CONSTRAINT [DF_disp_at] DEFAULT (sysutcdatetime()) NOT NULL,
    PRIMARY KEY CLUSTERED ([disposition_id] ASC)
);


GO

CREATE NONCLUSTERED INDEX [IX_disp_alert]
    ON [ops].[alert_disposition]([alert_id] ASC);


GO

