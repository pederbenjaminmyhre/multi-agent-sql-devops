-- Test SQL file to trigger the review pipeline
CREATE PROCEDURE dbo.GetRecentProducts
AS
SELECT *
FROM Products p
JOIN OrderItems oi ON oi.ProductID = p.ProductID
WHERE p.IsActive = 1
ORDER BY p.ProductName

SELECT @@IDENTITY AS LastInsert
