CREATE TABLE [ops].[kyc_action] (
    [action_id]       BIGINT         IDENTITY (1, 1) NOT NULL,
    [customer_id]     VARCHAR (64)   NOT NULL,
    [action]          VARCHAR (64)   NOT NULL,
    [owner]           NVARCHAR (256) NULL,
    [next_review_due] DATE           NULL,
    [at]              DATETIME2 (3)  CONSTRAINT [DF_kyc_at] DEFAULT (sysutcdatetime()) NOT NULL,
    PRIMARY KEY CLUSTERED ([action_id] ASC)
);


GO

