--[[
Possible return values:
	1:  user has permissions
	0:  user does not have 1 or more permissions
	-1: permissions are not cached
--]]

local tPermissionsKey = "permissions:" .. ARGV[1] .. ":" .. ARGV[2]
local tPermissions = redis.call("GET", tPermissionsKey)

if not tPermissions then
	return -1
end

-- refresh ttl, 1 hour
redis.call("EXPIRE", tPermissionsKey, 3600)

if bit.band(tPermissions, ARGV[3]) == tonumber(ARGV[3]) then
	return 1
else
	return 0
end
