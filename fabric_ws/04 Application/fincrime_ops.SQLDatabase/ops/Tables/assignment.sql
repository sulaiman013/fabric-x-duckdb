CREATE TABLE [ops].[assignment] (
    [item_type]   VARCHAR (32)   NOT NULL,
    [item_id]     VARCHAR (64)   NOT NULL,
    [assignee]    NVARCHAR (256) NOT NULL,
    [assigned_at] DATETIME2 (3)  CONSTRAINT [DF_asg_at] DEFAULT (sysutcdatetime()) NOT NULL,
    CONSTRAINT [PK_assignment] PRIMARY KEY CLUSTERED ([item_type] ASC, [item_id] ASC)
);


GO

