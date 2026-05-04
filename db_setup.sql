IF DB_ID('StudyDesk') IS NULL
BEGIN
    CREATE DATABASE StudyDesk;
END
GO

USE StudyDesk;
GO

IF OBJECT_ID('dbo.Users', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Users (
        UserID INT IDENTITY(1,1) PRIMARY KEY,
        Name VARCHAR(100) NOT NULL,
        Age INT NOT NULL,
        Email VARCHAR(100) NOT NULL,
        CreatedAt DATETIME DEFAULT GETDATE()
    );
END
GO
