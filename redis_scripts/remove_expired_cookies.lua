local tUserKey = "user_cookies:" .. KEYS[1]
local tCookies = redis.call("SMEMBERS", tUserKey)
local tExpired = {}

for tKey, tValue in pairs(tCookies) do
	if redis.call("EXISTS", "AIOHTTP_SESSION_" .. tValue) == 0 then
		table.insert(tExpired, tValue)
	end
end

-- check if there are no expired items
if next(tExpired) == nil then
	return 0
end

return redis.call("SREM", tUserKey, unpack(tExpired))
