CREATE TABLE [ops].[case] (
    [case_id]          VARCHAR (64)    NOT NULL,
    [_mirror_row_id]   BIGINT          NOT NULL,
    [state]            VARCHAR (32)    NOT NULL,
    [owner]            NVARCHAR (256)  NULL,
    [sla_due_at]       DATETIME2 (3)   NULL,
    [resolution]       VARCHAR (64)    NULL,
    [recovered_amount] DECIMAL (18, 2) NULL,
    [opened_at]        DATETIME2 (3)   CONSTRAINT [DF_case_at] DEFAULT (sysutcdatetime()) NOT NULL,
    PRIMARY KEY CLUSTERED ([case_id] ASC)
);


GO

