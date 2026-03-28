-- Intentionally flawed SQL for testing the review pipeline
CREATE PROCEDURE dbo.GetCustomerOrders
    @CustID INT
AS
SELECT *
FROM Orders o
JOIN Customers c ON o.CustomerID = c.CustomerID
JOIN OrderItems oi ON oi.OrderID = o.OrderID
JOIN Products p ON p.ProductID = oi.ProductID
WHERE c.CustomerID = @CustID
  AND o.Status = 'Shipped'
ORDER BY o.OrderDate DESC

SET ROWCOUNT 100

SELECT @@IDENTITY AS LastID
