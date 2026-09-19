CREATE TABLE [ops].[case_event] (
    [event_id]   BIGINT         IDENTITY (1, 1) NOT NULL,
    [case_id]    VARCHAR (64)   NOT NULL,
    [from_state] VARCHAR (32)   NULL,
    [to_state]   VARCHAR (32)   NOT NULL,
    [actor]      NVARCHAR (256) NOT NULL,
    [note]       NVARCHAR (512) NULL,
    [at]         DATETIME2 (3)  CONSTRAINT [DF_evt_at] DEFAULT (sysutcdatetime()) NOT NULL,
    PRIMARY KEY CLUSTERED ([event_id] ASC)
);


GO

CREATE NONCLUSTERED INDEX [IX_evt_case]
    ON [ops].[case_event]([case_id] ASC, [at] ASC);


GO

