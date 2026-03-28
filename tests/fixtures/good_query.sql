SET NOCOUNT ON;

SELECT
    o.OrderID,
    o.OrderDate,
    o.TotalAmount,
    o.Status,
    c.FirstName,
    c.LastName
FROM dbo.Orders AS o
INNER JOIN dbo.Customers AS c
    ON o.CustomerID = c.CustomerID
WHERE o.CustomerID = @CustomerID
    AND o.Status = N'Shipped'
ORDER BY o.OrderDate DESC;
